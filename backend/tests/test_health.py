from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_health_endpoint(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "SENTINEL" in payload["service"]


def test_status_endpoint(client) -> None:
    response = client.get("/api/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["app_name"] == "SENTINEL"
    assert payload["phase"] == "Phase 1 — Foundation"
    assert payload["ai_model_connected"] is False
