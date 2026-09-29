from __future__ import annotations

import pytest
from app.ai.model_registry import ModelRegistry


def test_model_registry_contains_mandatory_candidates() -> None:
    reg = ModelRegistry()
    candidates = reg.list_candidates()
    candidate_ids = {c.id for c in candidates}

    assert "yolo-x" in candidate_ids
    assert "yolov8-detection" in candidate_ids
    assert "yolov10-detection" in candidate_ids
    assert "yolov11-detection" in candidate_ids


def test_candidate_official_sources_and_metrics_separation() -> None:
    reg = ModelRegistry()
    yolox = reg.get_candidate("yolo-x")
    assert yolox is not None
    assert yolox.license == "Apache-2.0"
    assert yolox.task == "Object Detection"
    assert "Qualcomm AI Hub" in yolox.source
    assert yolox.format == "ONNX"
    assert yolox.input_width == 640
    assert yolox.input_height == 640

    # Reference metrics from Qualcomm AI Hub must be populated
    assert yolox.reference_metrics.reference_latency_ms is not None
    assert yolox.reference_metrics.reference_throughput_fps is not None
    assert "Snapdragon" in yolox.reference_metrics.reference_device

    # Our measured metrics must remain strictly null until real test
    assert yolox.our_metrics.our_latency_ms is None
    assert yolox.our_metrics.our_throughput_fps is None
    assert yolox.our_metrics.our_device is None
