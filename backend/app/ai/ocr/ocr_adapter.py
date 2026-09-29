from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any
import numpy as np
from PIL import Image

from app.ai.ocr.geometry import polygon_to_bbox, sort_reading_order
from app.schemas.ocr import OCRModelMetadata, OCRTimingMetrics, TextRegion

logger = logging.getLogger("sentinel.ai.ocr.adapter")


class OCRModelAdapter(ABC):
    """Abstract interface for local OCR detection and recognition engines."""

    @abstractmethod
    def load(self, languages: list[str] | None = None) -> None:
        """Loads detector and recognizer models into memory."""
        pass

    @abstractmethod
    def unload(self) -> None:
        """Unloads models and releases device memory."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if model libraries and weights are installable or present."""
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """Returns True if active inference sessions are ready."""
        pass

    @abstractmethod
    def get_metadata(self) -> OCRModelMetadata:
        """Returns architecture and model information."""
        pass

    @abstractmethod
    def process_image(
        self,
        image_data: Image.Image | np.ndarray | bytes,
        confidence_threshold: float = 0.2,
    ) -> dict[str, Any]:
        """Runs end-to-end OCR pass with stage timing breakdowns."""
        pass


class EasyOCRAdapter(OCRModelAdapter):
    """
    Qualcomm AI Hub-aligned two-stage OCR pipeline:
    1. Text Detection: CRAFT (Character Region Awareness for Text Detection)
    2. Text Recognition: CRNN (Convolutional Recurrent Neural Network)
    """

    def __init__(self, default_languages: list[str] | None = None) -> None:
        self._languages = default_languages or ["en"]
        self._reader: Any = None
        self._is_loaded = False
        self._provider = "CPUExecutionProvider"
        self._npu_verified = False

    def is_available(self) -> bool:
        try:
            import easyocr
            return True
        except ImportError:
            return False

    def is_loaded(self) -> bool:
        return self._is_loaded and self._reader is not None

    def get_metadata(self) -> OCRModelMetadata:
        return OCRModelMetadata(
            name="EasyOCR (Qualcomm AI Hub Target Architecture)",
            detector="CRAFT (Character Region Awareness for Text Detection)",
            recognizer="CRNN (Convolutional Recurrent Neural Network with CTC)",
            runtime="Local PyTorch Engine (QNN Target Compatible)",
            license="Apache-2.0",
            languages=self._languages,
            input_resolution="Dynamic Aspect-Ratio Preserving",
        )

    def get_active_provider(self) -> str:
        return self._provider

    def is_npu_verified(self) -> bool:
        return self._npu_verified

    def load(self, languages: list[str] | None = None) -> None:
        if languages:
            self._languages = languages
        try:
            import easyocr
            logger.info("Initializing EasyOCR reader for languages: %s", self._languages)
            # Disable verbose progress bar to avoid Windows charmap encoding issues
            self._reader = easyocr.Reader(self._languages, gpu=False, verbose=False)
            self._is_loaded = True
            logger.info("EasyOCR detector and recognizer loaded successfully into memory.")
        except Exception as e:
            self._is_loaded = False
            self._reader = None
            logger.exception("Failed to initialize EasyOCR reader: %s", e)
            raise RuntimeError(f"OCR model initialization failed: {e}") from e

    def unload(self) -> None:
        self._reader = None
        self._is_loaded = False
        import gc
        gc.collect()
        logger.info("EasyOCR model unloaded from memory.")

    def process_image(
        self,
        image_data: Image.Image | np.ndarray | bytes,
        confidence_threshold: float = 0.2,
    ) -> dict[str, Any]:
        if not self.is_loaded():
            self.load()

        total_start = time.perf_counter()

        # 1. Preprocessing
        prep_start = time.perf_counter()
        if isinstance(image_data, bytes):
            import io
            pil_img = Image.open(io.BytesIO(image_data))
        elif isinstance(image_data, np.ndarray):
            pil_img = Image.fromarray(image_data)
        elif isinstance(image_data, Image.Image):
            pil_img = image_data
        else:
            raise ValueError(f"Unsupported image type: {type(image_data)}")

        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")

        orig_w, orig_h = pil_img.size
        img_arr = np.array(pil_img)
        preprocess_ms = round((time.perf_counter() - prep_start) * 1000.0, 3)

        # 2. Text Detection stage (CRAFT)
        det_start = time.perf_counter()
        try:
            horizontal_list, free_list = self._reader.detect(img_arr)
        except Exception as e:
            logger.exception("CRAFT detector stage failed: %s", e)
            raise RuntimeError(f"OCR text detector stage failed: {e}") from e
        detector_ms = round((time.perf_counter() - det_start) * 1000.0, 3)

        # 3. Text Recognition stage (CRNN)
        rec_start = time.perf_counter()
        try:
            boxes = horizontal_list[0] if horizontal_list else []
            free_boxes = free_list[0] if free_list else []
            raw_results = self._reader.recognize(img_arr, horizontal_list=boxes, free_list=free_boxes)
        except Exception as e:
            logger.exception("CRNN recognizer stage failed: %s", e)
            raise RuntimeError(f"OCR text recognizer stage failed: {e}") from e
        recognizer_ms = round((time.perf_counter() - rec_start) * 1000.0, 3)

        # 4. Postprocessing & Coordinate Mapping
        post_start = time.perf_counter()
        raw_regions: list[dict[str, Any]] = []
        region_idx = 1

        for item in raw_results:
            # item format: (bbox_polygon, text, confidence)
            polygon_pts, text_str, conf = item
            clean_text = str(text_str).strip()
            conf_val = float(conf)

            # Strict confidence threshold filter
            if not clean_text or conf_val < confidence_threshold:
                continue

            # Convert numpy polygon to standard python float list
            poly_list = [[float(pt[0]), float(pt[1])] for pt in polygon_pts]

            # Reusable geometry conversion with exact image bounds clamp
            bbox = polygon_to_bbox(poly_list, orig_w, orig_h)

            raw_regions.append({
                "id": f"region-{region_idx}",
                "text": clean_text,
                "confidence": round(conf_val, 4),
                "bbox": bbox,
                "polygon": poly_list,
                "language": self._languages[0] if self._languages else "en",
            })
            region_idx += 1

        # Deterministic top-to-bottom, left-to-right reading order sorting
        ordered_regions = sort_reading_order(raw_regions)

        full_text_lines = [r["text"] for r in ordered_regions]
        full_text = " ".join(full_text_lines)

        postprocess_ms = round((time.perf_counter() - post_start) * 1000.0, 3)
        total_ms = round((time.perf_counter() - total_start) * 1000.0, 3)

        timing = OCRTimingMetrics(
            preprocess_ms=preprocess_ms,
            detector_ms=detector_ms,
            recognizer_ms=recognizer_ms,
            postprocess_ms=postprocess_ms,
            total_ms=total_ms,
        )

        typed_regions = [
            TextRegion(
                id=r["id"],
                text=r["text"],
                confidence=r["confidence"],
                bbox=r["bbox"],
                polygon=r["polygon"],
                language=r.get("language", "en"),
                reading_order=r.get("reading_order"),
            )
            for r in ordered_regions
        ]

        return {
            "regions": typed_regions,
            "full_text": full_text,
            "region_count": len(typed_regions),
            "timing": timing,
            "image_dims": {"width": orig_w, "height": orig_h},
            "active_provider": self._provider,
            "npu_verified": self._npu_verified,
        }
