from __future__ import annotations

import logging
from typing import Any
import numpy as np
from PIL import Image

from app.ai.pipeline import VisionModelAdapter
from app.ai.vision.coco_classes import get_coco_label

logger = logging.getLogger("sentinel.yolox_adapter")


class YOLOXAdapter(VisionModelAdapter):
    """
    Model adapter for YOLO-X object detectors (Qualcomm AI Hub Windows reference model).
    Handles aspect-ratio preserving letterbox preprocessing and anchor unstriding with NMS.
    """

    def __init__(self, model_width: int = 640, model_height: int = 640) -> None:
        self.model_width = model_width
        self.model_height = model_height
        self._grid_cache: tuple[int, int, np.ndarray, np.ndarray] | None = None

    def get_model_metadata(self) -> dict[str, Any]:
        return {
            "name": "YOLO-X",
            "version": "Small",
            "source": "Qualcomm AI Hub Windows Reference (object_detection_windows_cpp)",
            "license": "Apache-2.0",
            "format": "ONNX",
            "input_resolution": f"{self.model_width}x{self.model_height}",
            "input_shape": [1, 3, self.model_height, self.model_width],
            "classes": 80,
            "quantization": "FP32 / INT8 Target",
        }

    def preprocess(self, image_data: Image.Image | bytes | np.ndarray) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
        """
        Prepares image for YOLO-X inference:
        1. Ensures 3-channel RGB image.
        2. Computes scale factor preserving aspect ratio.
        3. Resizes image.
        4. Letterbox pads with value 114 to target dimensions (model_width x model_height).
        5. Converts RGB to BGR and transposes to [1, 3, H, W] float32.
        """
        if isinstance(image_data, bytes):
            import io
            pil_img = Image.open(io.BytesIO(image_data))
        elif isinstance(image_data, np.ndarray):
            pil_img = Image.fromarray(image_data)
        elif isinstance(image_data, Image.Image):
            pil_img = image_data
        else:
            raise ValueError(f"Unsupported image_data type: {type(image_data)}")

        # Ensure RGB
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")

        orig_w, orig_h = pil_img.size

        # Compute scale preserving aspect ratio
        scale = min(self.model_width / orig_w, self.model_height / orig_h)
        resized_w = int(orig_w * scale)
        resized_h = int(orig_h * scale)

        # High-quality resize
        resized_img = pil_img.resize((resized_w, resized_h), Image.Resampling.BILINEAR)

        # Convert to numpy array in BGR order (Megvii YOLOX & OpenCV convention)
        rgb_arr = np.array(resized_img, dtype=np.uint8)
        bgr_arr = rgb_arr[:, :, ::-1]

        # Letterbox padding with constant 114
        padded = np.ones((self.model_height, self.model_width, 3), dtype=np.uint8) * 114
        padded[:resized_h, :resized_w] = bgr_arr

        # Transpose HWC to CHW and add batch dimension
        chw = padded.transpose((2, 0, 1))
        tensor = np.ascontiguousarray(chw[None, :, :, :], dtype=np.float32)

        metadata = {
            "original_width": orig_w,
            "original_height": orig_h,
            "model_width": self.model_width,
            "model_height": self.model_height,
            "scale": scale,
            "resized_width": resized_w,
            "resized_height": resized_h,
        }

        return {"images": tensor}, metadata

    def _get_grids_and_strides(self, img_height: int, img_width: int) -> tuple[np.ndarray, np.ndarray]:
        if self._grid_cache and self._grid_cache[0] == img_height and self._grid_cache[1] == img_width:
            return self._grid_cache[2], self._grid_cache[3]

        strides = [8, 16, 32]
        grids = []
        expanded_strides = []

        for stride in strides:
            h_size = img_height // stride
            w_size = img_width // stride
            xv, yv = np.meshgrid(np.arange(w_size), np.arange(h_size))
            grid = np.stack((xv, yv), axis=2).reshape(1, -1, 2)
            grids.append(grid)
            shape = grid.shape[:2]
            expanded_strides.append(np.full((*shape, 1), stride))

        concat_grids = np.concatenate(grids, axis=1)
        concat_strides = np.concatenate(expanded_strides, axis=1)
        self._grid_cache = (img_height, img_width, concat_grids, concat_strides)
        return concat_grids, concat_strides

    def _apply_nms(
        self, boxes: np.ndarray, scores: np.ndarray, iou_threshold: float
    ) -> list[int]:
        """Performs Non-Maximum Suppression (NMS) in NumPy."""
        if len(boxes) == 0:
            return []

        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]

        areas = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
        order = scores.argsort()[::-1]

        keep: list[int] = []
        while order.size > 0:
            i = int(order[0])
            keep.append(i)

            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h
            union = areas[i] + areas[order[1:]] - inter
            iou = inter / np.maximum(union, 1e-6)

            inds = np.where(iou <= iou_threshold)[0]
            order = order[inds + 1]

        return keep

    def postprocess(
        self,
        raw_outputs: dict[str, np.ndarray] | np.ndarray,
        metadata: dict[str, Any],
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
    ) -> list[dict[str, Any]]:
        """
        Decodes YOLOX anchor outputs, unstrides bounding boxes, maps coordinates
        back to original image space, and applies class-aware NMS.
        """
        if isinstance(raw_outputs, dict):
            output = list(raw_outputs.values())[0]
        else:
            output = raw_outputs

        orig_w = metadata["original_width"]
        orig_h = metadata["original_height"]
        scale = metadata["scale"]
        model_w = metadata["model_width"]
        model_h = metadata["model_height"]

        # Output shape: [1, N, 85]
        predictions = output.copy()
        grids, expanded_strides = self._get_grids_and_strides(model_h, model_w)

        # Unstride coordinates
        predictions[..., :2] = (predictions[..., :2] + grids) * expanded_strides
        predictions[..., 2:4] = np.exp(predictions[..., 2:4]) * expanded_strides

        pred_batch = predictions[0]  # [N, 85]
        boxes_xywh = pred_batch[:, :4]
        obj_conf = pred_batch[:, 4:5]
        cls_probs = pred_batch[:, 5:85]

        # Calculate final class confidence scores
        scores = obj_conf * cls_probs  # [N, 80]

        # Find best class per box
        cls_ids = np.argmax(scores, axis=1)
        max_scores = scores[np.arange(len(cls_ids)), cls_ids]

        # Filter by confidence threshold
        mask = max_scores >= confidence_threshold
        if not np.any(mask):
            return []

        filt_boxes = boxes_xywh[mask]
        filt_scores = max_scores[mask]
        filt_cls_ids = cls_ids[mask]

        # Convert [cx, cy, w, h] to [x1, y1, x2, y2]
        cx, cy, w, h = (
            filt_boxes[:, 0],
            filt_boxes[:, 1],
            filt_boxes[:, 2],
            filt_boxes[:, 3],
        )
        x1 = cx - w / 2.0
        y1 = cy - h / 2.0
        x2 = cx + w / 2.0
        y2 = cy + h / 2.0

        # Map back to original image space
        x1 = x1 / scale
        y1 = y1 / scale
        x2 = x2 / scale
        y2 = y2 / scale

        # Clip coordinates to original image bounds
        x1 = np.clip(x1, 0.0, float(orig_w))
        y1 = np.clip(y1, 0.0, float(orig_h))
        x2 = np.clip(x2, 0.0, float(orig_w))
        y2 = np.clip(y2, 0.0, float(orig_h))

        boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1)

        # Class-aware NMS
        final_detections: list[dict[str, Any]] = []
        unique_classes = np.unique(filt_cls_ids)

        for c in unique_classes:
            c_mask = filt_cls_ids == c
            c_boxes = boxes_xyxy[c_mask]
            c_scores = filt_scores[c_mask]

            keep_indices = self._apply_nms(c_boxes, c_scores, iou_threshold)

            for idx in keep_indices:
                bx = c_boxes[idx]
                score = float(c_scores[idx])
                cid = int(c)

                # Normalized coordinates [0, 1] for frontend rendering
                x_min_norm = max(0.0, min(1.0, bx[0] / orig_w))
                y_min_norm = max(0.0, min(1.0, bx[1] / orig_h))
                x_max_norm = max(0.0, min(1.0, bx[2] / orig_w))
                y_max_norm = max(0.0, min(1.0, bx[3] / orig_h))

                x_val = round(x_min_norm, 4)
                y_val = round(y_min_norm, 4)
                w_val = round(max(0.0, x_max_norm - x_min_norm), 4)
                h_val = round(max(0.0, y_max_norm - y_min_norm), 4)

                final_detections.append(
                    {
                        "class_id": cid,
                        "label": get_coco_label(cid),
                        "confidence": round(score, 4),
                        "bbox": {
                            "x": x_val,
                            "y": y_val,
                            "width": w_val,
                            "height": h_val,
                            "x_min": x_val,
                            "y_min": y_val,
                            "x_max": round(x_max_norm, 4),
                            "y_max": round(y_max_norm, 4),
                            "x_abs_min": round(float(bx[0]), 2),
                            "y_abs_min": round(float(bx[1]), 2),
                            "x_abs_max": round(float(bx[2]), 2),
                            "y_abs_max": round(float(bx[3]), 2),
                        },
                    }
                )

        # Sort descending by confidence
        final_detections.sort(key=lambda d: d["confidence"], reverse=True)
        return final_detections
