from __future__ import annotations

import pytest


def test_hardware_diagnostics_route(client) -> None:
    res = client.get("/api/system/hardware")
    assert res.status_code == 200
    data = res.json()
    assert "processor_name" in data
    assert "system_architecture" in data
    assert "ram_total_gb" in data
    assert "snapdragon_detected" in data
    assert "target_comparison" in data


def test_runtime_diagnostics_route(client) -> None:
    res = client.get("/api/system/runtime")
    assert res.status_code == 200
    data = res.json()
    assert "python_version" in data
    assert "onnxruntime_installed" in data
    assert "available_providers" in data
    assert "provider_states" in data
    assert data["npu_execution_verified"] is False
    assert data["verification_method"] == "NOT_TESTED"


def test_full_diagnostics_route(client) -> None:
    res = client.get("/api/system/diagnostics")
    assert res.status_code == 200
    data = res.json()
    assert "hardware" in data
    assert "runtime" in data
    assert "target_profile" in data
    assert "summary" in data


def test_environment_report_route(client) -> None:
    res = client.get("/api/system/environment-report")
    assert res.status_code == 200
    data = res.json()
    assert "report" in data
    assert "SENTINEL AI ENVIRONMENT REPORT" in data["report"]
    assert "Hardware" in data["report"]
    assert "YOLO-X" in data["report"]


def test_model_candidates_route(client) -> None:
    res = client.get("/api/models/candidates")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 4
    candidate_ids = [c["id"] for c in data]
    assert "yolo-x" in candidate_ids


def test_model_selection_route(client) -> None:
    res = client.get("/api/models/selection")
    assert res.status_code == 200
    data = res.json()
    assert data["recommended_first_candidate"] == "yolo-x"
    assert "candidates" in data
    assert len(data["candidates"]) >= 4
