from __future__ import annotations

import io
from pathlib import Path
import pytest
import numpy as np
from PIL import Image

from app.ai.vision.coco_classes import COCO_CLASSES, get_coco_label
from app.ai.vision.inference_engine import inference_engine, ModelLifecycleState, YOLOXInferenceEngine
from app.ai.vision.onnx_runtime_adapter import ONNXRuntimeAdapter
from app.ai.vision.yolox_adapter import YOLOXAdapter


def test_coco_classes_ontology() -> None:
    assert len(COCO_CLASSES) == 80
    assert get_coco_label(0) == "person"
    assert get_coco_label(62) == "tv"
    assert get_coco_label(63) == "laptop"
    assert get_coco_label(999) == "unknown_class_999"


def test_yolox_letterbox_preprocessing_aspect_ratios() -> None:
    adapter = YOLOXAdapter(model_width=640, model_height=640)

    # 1. Square image (1:1)
    sq = Image.new("RGB", (500, 500), color=(100, 150, 200))
    inp, meta = adapter.preprocess(sq)
    assert inp["images"].shape == (1, 3, 640, 640)
    assert meta["scale"] == 640 / 500
    assert meta["resized_width"] == 640
    assert meta["resized_height"] == 640

    # 2. Landscape image (16:9)
    land = Image.new("RGB", (1280, 720), color=(50, 100, 150))
    inp_l, meta_l = adapter.preprocess(land)
    assert inp_l["images"].shape == (1, 3, 640, 640)
    assert meta_l["scale"] == 640 / 1280
    assert meta_l["resized_width"] == 640
    assert meta_l["resized_height"] == 360  # 720 * 0.5

    # 3. Portrait image (9:16)
    port = Image.new("RGB", (720, 1280), color=(20, 40, 60))
    inp_p, meta_p = adapter.preprocess(port)
    assert inp_p["images"].shape == (1, 3, 640, 640)
    assert meta_p["scale"] == 640 / 1280
    assert meta_p["resized_height"] == 640
    assert meta_p["resized_width"] == 360  # 720 * 0.5

    # 4. Standard 4:3 image
    four_three = Image.new("RGB", (1200, 900), color=(30, 60, 90))
    inp_43, meta_43 = adapter.preprocess(four_three)
    assert inp_43["images"].shape == (1, 3, 640, 640)
    assert round(meta_43["scale"], 4) == round(640 / 1200, 4)
    assert meta_43["resized_width"] == 640
    assert meta_43["resized_height"] == int(900 * (640 / 1200))


def test_bounding_box_accuracy_all_aspect_ratios_and_positions() -> None:
    """
    Requirement 8:
    Verify coordinate transform accuracy across 16:9, 4:3, 1:1, portrait
    and positions: top-left, top-right, bottom-left, bottom-right, center.
    Bounding boxes must map accurately back to original image dimensions.
    """
    adapter = YOLOXAdapter(model_width=640, model_height=640)

    test_aspects = [
        ("16_9", 1920, 1080),
        ("4_3", 1200, 900),
        ("1_1", 800, 800),
        ("portrait", 720, 1280),
    ]

    for aspect_name, orig_w, orig_h in test_aspects:
        scale = min(640 / orig_w, 640 / orig_h)
        meta = {
            "original_width": orig_w,
            "original_height": orig_h,
            "model_width": 640,
            "model_height": 640,
            "scale": scale,
            "resized_width": int(orig_w * scale),
            "resized_height": int(orig_h * scale),
        }

        # Define 5 object box positions in original image space
        box_w, box_h = 100.0, 80.0
        positions = {
            "top_left": (0.0, 0.0, box_w, box_h),
            "top_right": (orig_w - box_w, 0.0, orig_w, box_h),
            "bottom_left": (0.0, orig_h - box_h, box_w, orig_h),
            "bottom_right": (orig_w - box_w, orig_h - box_h, orig_w, orig_h),
            "center": (orig_w / 2 - box_w / 2, orig_h / 2 - box_h / 2, orig_w / 2 + box_w / 2, orig_h / 2 + box_h / 2),
        }

        grids, strides = adapter._get_grids_and_strides(640, 640)

        for pos_name, (x1, y1, x2, y2) in positions.items():
            # Convert to model canvas space
            mx1 = x1 * scale
            my1 = y1 * scale
            mx2 = x2 * scale
            my2 = y2 * scale
            mcx = (mx1 + mx2) / 2.0
            mcy = (my1 + my2) / 2.0
            mw = mx2 - mx1
            mh = my2 - my1

            # Synthetic single prediction output
            dummy_output = np.zeros((1, 8400, 85), dtype=np.float32)

            # Map into anchor index 0 (stride 8, grid 0, 0)
            stride_0 = float(strides[0, 0, 0])
            grid_x_0 = float(grids[0, 0, 0])
            grid_y_0 = float(grids[0, 0, 1])

            dummy_output[0, 0, 0] = (mcx / stride_0) - grid_x_0
            dummy_output[0, 0, 1] = (mcy / stride_0) - grid_y_0
            dummy_output[0, 0, 2] = np.log(max(1e-4, mw / stride_0))
            dummy_output[0, 0, 3] = np.log(max(1e-4, mh / stride_0))
            dummy_output[0, 0, 4] = 1.0  # obj_conf
            dummy_output[0, 0, 5 + 63] = 1.0  # laptop

            dets = adapter.postprocess(dummy_output, metadata=meta, confidence_threshold=0.5)
            assert len(dets) == 1, f"Failed detection for {aspect_name} {pos_name}"
            d = dets[0]
            b = d["bbox"]

            # Verify unstriding and reverse scaling mapped back accurately within float tolerance
            assert abs(b["x_abs_min"] - x1) < 1.0, f"X min mismatch {aspect_name} {pos_name}: {b['x_abs_min']} vs {x1}"
            assert abs(b["y_abs_min"] - y1) < 1.0, f"Y min mismatch {aspect_name} {pos_name}: {b['y_abs_min']} vs {y1}"
            assert abs(b["x_abs_max"] - x2) < 1.0, f"X max mismatch {aspect_name} {pos_name}: {b['x_abs_max']} vs {x2}"
            assert abs(b["y_abs_max"] - y2) < 1.0, f"Y max mismatch {aspect_name} {pos_name}: {b['y_abs_max']} vs {y2}"

            # Verify normalized boundaries [0, 1]
            assert 0.0 <= b["x"] <= 1.0
            assert 0.0 <= b["y"] <= 1.0
            assert 0.0 <= b["width"] <= 1.0
            assert 0.0 <= b["height"] <= 1.0


def test_yolox_nms_suppression() -> None:
    adapter = YOLOXAdapter(model_width=640, model_height=640)
    meta = {
        "original_width": 640,
        "original_height": 640,
        "model_width": 640,
        "model_height": 640,
        "scale": 1.0,
        "resized_width": 640,
        "resized_height": 640,
    }

    dummy_output = np.zeros((1, 8400, 85), dtype=np.float32)
    # Two overlapping detections for class 0 (person)
    dummy_output[0, 0, 2:4] = 2.5  # w, h -> exp(2.5)*8 ~ 97 pixels
    dummy_output[0, 0, 4] = 0.90  # obj
    dummy_output[0, 0, 5] = 0.90  # class 0 (person)
    dummy_output[0, 1, 2:4] = 2.5  # w, h -> exp(2.5)*8 ~ 97 pixels
    dummy_output[0, 1, 4] = 0.85  # obj
    dummy_output[0, 1, 5] = 0.90  # class 0 (person)

    dets = adapter.postprocess(dummy_output, metadata=meta, confidence_threshold=0.5, iou_threshold=0.45)
    # NMS should keep only the highest scoring box
    assert len(dets) == 1
    assert dets[0]["confidence"] == round(0.90 * 0.90, 4)


def test_live_inference_engine_execution() -> None:
    """Verifies that real YOLO-X ONNX model loads and runs inference on host CPU."""
    test_img = Image.new("RGB", (640, 480), color=(200, 200, 200))
    res = inference_engine.detect_objects(test_img)

    assert "detections" in res
    assert "timing" in res
    assert res["timing"]["inference_ms"] > 0
    assert res["timing"]["total_ms"] > 0
    assert res["active_provider"] == "CPUExecutionProvider"
    assert res["is_npu_verified"] is False
    assert inference_engine.state == ModelLifecycleState.READY


def test_live_yolox_real_test_assets() -> None:
    """
    Requirement 5: Real Inference Verification.
    Runs live inference on real test images containing everyday COCO objects:
    laptop, phone, book, bottle, person, keyboard, chair.
    """
    root_assets = Path("backend/tests/test_assets")
    assert root_assets.exists(), "Test assets directory missing"

    # 1. 16:9 Workspace Image (contains laptop, mouse, cup)
    p_16_9 = root_assets / "workspace_16_9.jpg"
    img_16_9 = Image.open(p_16_9)
    res_16_9 = inference_engine.detect_objects(img_16_9, confidence_threshold=0.25)
    labels_16_9 = [d["label"] for d in res_16_9["detections"]]
    assert "laptop" in labels_16_9
    assert "mouse" in labels_16_9
    assert "cup" in labels_16_9
    assert res_16_9["timing"]["inference_ms"] > 0

    # 2. 4:3 Desk Image (contains cell phone, bottle, book)
    p_4_3 = root_assets / "desk_4_3.jpg"
    img_4_3 = Image.open(p_4_3)
    res_4_3 = inference_engine.detect_objects(img_4_3, confidence_threshold=0.25)
    labels_4_3 = [d["label"] for d in res_4_3["detections"]]
    assert "cell phone" in labels_4_3
    assert "bottle" in labels_4_3
    assert "book" in labels_4_3

    # 3. Portrait Image (contains person, tv, chair, keyboard)
    p_port = root_assets / "workspace_portrait.jpg"
    img_port = Image.open(p_port)
    res_port = inference_engine.detect_objects(img_port, confidence_threshold=0.25)
    labels_port = [d["label"] for d in res_port["detections"]]
    assert "person" in labels_port
    assert "tv" in labels_port
    assert "keyboard" in labels_port
    assert "chair" in labels_port

    # Verify telemetry structure
    assert res_16_9["active_provider"] == "CPUExecutionProvider"
    assert res_16_9["is_npu_verified"] is False


def test_inference_benchmark_suite() -> None:
    test_img = Image.new("RGB", (640, 480), color=(150, 150, 150))
    record = inference_engine.run_benchmark(test_img, warmup_runs=2, measured_runs=3)

    assert record.model_name.startswith("YOLO-X")
    assert record.average_inference_ms is not None
    assert record.average_inference_ms > 0
    assert record.preprocess_ms is not None
    assert record.postprocess_ms is not None
    assert record.total_pipeline_ms is not None
    assert record.throughput is not None
    assert "CPUExecutionProvider" in record.execution_provider


def test_vision_analyze_api_flow(client) -> None:
    # 1. Upload a valid test image
    img = Image.new("RGB", (400, 300), color=(80, 120, 160))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    upload_res = client.post(
        "/api/vision/upload",
        files={"file": ("test_desk.png", buf.getvalue(), "image/png")},
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["file_id"]

    # 2. Run real analysis
    analyze_res = client.post("/api/vision/analyze", json={"file_id": file_id})
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    assert data["status"] == "SUCCESS"
    assert "YOLO-X" in data["model"]["name"]
    assert data["runtime"] == "ONNX Runtime v1.30.0"
    assert data["verification"]["npu_verified"] is False
    assert "LOCAL • CPU" in data["verification"]["display_label"]
    assert data["timing"]["inference_ms"] > 0
    assert data["image"]["original_width"] == 400
    assert data["image"]["original_height"] == 300
    assert isinstance(data["objects"], list)


def test_vision_confidence_threshold_filtering(client) -> None:
    """Tests that confidence_threshold actively filters detections."""
    test_assets = Path("backend/tests/test_assets/workspace_16_9.jpg")
    img = Image.open(test_assets)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    upload_res = client.post(
        "/api/vision/upload",
        files={"file": ("workspace.jpg", buf.getvalue(), "image/jpeg")},
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["file_id"]

    # Low threshold: returns multiple objects
    res_low = client.post(
        "/api/vision/analyze",
        json={"file_id": file_id, "confidence_threshold": 0.25},
    )
    assert res_low.status_code == 200
    count_low = len(res_low.json()["objects"])

    # High threshold: returns only high confidence objects
    res_high = client.post(
        "/api/vision/analyze",
        json={"file_id": file_id, "confidence_threshold": 0.95},
    )
    assert res_high.status_code == 200
    count_high = len(res_high.json()["objects"])

    assert count_high < count_low
    assert count_high >= 1
    assert all(obj["confidence"] >= 0.95 for obj in res_high.json()["objects"])


def test_vision_model_status_and_lifecycle_api(client) -> None:
    status_res = client.get("/api/vision/model/status")
    assert status_res.status_code == 200
    data = status_res.json()
    assert "YOLO-X" in data["model_name"]
    assert "state" in data

    # Unload
    unload_res = client.post("/api/vision/model/unload")
    assert unload_res.status_code == 200

    # Load again
    load_res = client.post("/api/vision/model/load")
    assert load_res.status_code == 200
    assert load_res.json()["state"] == "READY"


def test_mock_inference_engine_missing_model_error() -> None:
    """Verifies that missing model file triggers safe structured error."""
    engine = YOLOXInferenceEngine(model_filename="non_existent_model.onnx")
    engine.model_path = Path("models/vision/does_not_exist_file.onnx")

    assert engine.is_available() is False
    with pytest.raises(FileNotFoundError) as exc_info:
        engine.ensure_loaded()

    assert "not found" in str(exc_info.value)
    assert engine.state == ModelLifecycleState.UNAVAILABLE
