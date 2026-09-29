from __future__ import annotations

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.privacy import PrivacyPolicyUpdate
from app.services.privacy_service import privacy_service


def test_health_endpoint(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "SENTINEL" in data["service"]


def test_status_endpoint(client) -> None:
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "SENTINEL"
    assert data["indicators"]["vision"]["status"] == "Not Connected"
    assert data["indicators"]["memory"]["status"] == "Local Storage Ready"
    assert data["indicators"]["privacy"]["status"] == "Local Preference Enforced"
    assert data["indicators"]["npu"]["status"] == "Not Verified"
    assert data["npu_verified"] is False
    assert data["ai_model_connected"] is False


def test_ai_lab_models_and_hardware_truthful(client) -> None:
    response = client.get("/api/models/status")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert "vision" in data["models"]
    # Step 8 & 9: Vision and OCR models are now connected (AVAILABLE / READY)
    assert data["models"]["vision"]["status"] in ("AVAILABLE", "READY")
    assert "YOLO-X" in data["models"]["vision"]["name"]
    assert data["models"]["ocr"]["status"] in ("AVAILABLE", "READY")
    assert "EasyOCR" in data["models"]["ocr"]["name"]
    # Other models are still strictly NOT connected (PLANNED or MODEL_NOT_CONNECTED)
    assert data["models"]["speech"]["status"] in ("MODEL_NOT_CONNECTED", "PLANNED")
    assert data["models"]["multimodal"]["status"] in ("MODEL_NOT_CONNECTED", "PLANNED")
    hw = data["hardware"]
    assert "gpu" in hw
    assert "npu" in hw
    rt = data["runtime"]
    assert rt["npu_status"] == "Not verified"
    assert "execution_provider" in rt
    assert "YOLO-X" in rt["model_connection"]


def test_memory_crud_flow(client) -> None:
    privacy_service.update_policy(PrivacyPolicyUpdate(memory_enabled=True))

    # 1. Create Memory
    payload = {
        "title": "Temperature Monitoring Project",
        "content": "Uses ESP32, breadboard, and DHT11 sensor.",
        "category": "project",
        "source_type": "manual",
        "metadata": {"tags": ["hardware", "esp32", "dht11"]},
    }
    create_res = client.post("/api/memory", json=payload)
    assert create_res.status_code == 201
    created = create_res.json()
    mem_id = created["id"]
    assert created["title"] == "Temperature Monitoring Project"
    assert created["category"] == "project"

    # 2. Retrieve Memory
    get_res = client.get(f"/api/memory/{mem_id}")
    assert get_res.status_code == 200
    assert get_res.json()["content"] == "Uses ESP32, breadboard, and DHT11 sensor."

    # 3. List Memories with search
    list_res = client.get("/api/memory?search=ESP32")
    assert list_res.status_code == 200
    items = list_res.json()
    assert any(item["id"] == mem_id for item in items)

    # 4. Update Memory
    update_res = client.put(
        f"/api/memory/{mem_id}",
        json={"title": "Temperature Monitoring Project (v2)", "content": "Updated ESP32 with OLED display."},
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Temperature Monitoring Project (v2)"

    # 5. Delete Memory
    del_res = client.delete(f"/api/memory/{mem_id}")
    assert del_res.status_code == 200

    # 6. Verify 404 after deletion
    verify_res = client.get(f"/api/memory/{mem_id}")
    assert verify_res.status_code == 404


def test_project_crud_flow(client) -> None:
    # 1. Create Project
    res = client.post("/api/projects", json={"name": "Embedded IoT Desk", "description": "Desk sensors"})
    assert res.status_code == 201
    proj = res.json()
    proj_id = proj["id"]
    assert proj["name"] == "Embedded IoT Desk"

    # 2. List Projects
    list_res = client.get("/api/projects")
    assert list_res.status_code == 200
    assert any(p["id"] == proj_id for p in list_res.json())

    # 3. Delete Project
    del_res = client.delete(f"/api/projects/{proj_id}")
    assert del_res.status_code == 200


def test_conversation_and_chat_flow(client) -> None:
    # 1. Create Conversation
    conv_res = client.post("/api/chat/conversations", json={"title": "Workspace Discussion"})
    assert conv_res.status_code == 201
    conv = conv_res.json()
    conv_id = conv["id"]

    # 2. Send Chat Message
    payload = {
        "conversation_id": conv_id,
        "text": "What sensor am I using in my workspace?",
        "context": ["Workspace preview attached"],
    }
    chat_res = client.post("/api/chat", json=payload)
    assert chat_res.status_code == 200
    data = chat_res.json()
    assert "Qualcomm GenieX / QAIRT runtime is not available" in data["response"] or "Local AI model is not connected yet" in data["response"]
    assert data["status"] in ("MODEL_NOT_CONNECTED", "NOT_AVAILABLE_ON_HOST", "READY")

    # 3. Retrieve Conversation Messages
    msgs_res = client.get(f"/api/chat/conversations/{conv_id}/messages")
    assert msgs_res.status_code == 200
    msgs = msgs_res.json()
    assert len(msgs) == 2  # user + assistant


def test_file_upload_and_attachments(client) -> None:
    # 1. Valid PNG upload with correct image content
    from PIL import Image
    test_img = Image.new("RGB", (64, 64), color=(100, 150, 200))
    buf = io.BytesIO()
    test_img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    upload_res = client.post(
        "/api/files/upload",
        files={"file": ("test_circuit.png", io.BytesIO(png_bytes), "image/png")},
    )
    assert upload_res.status_code == 201
    upload_data = upload_res.json()
    file_id = upload_data["file_id"]
    assert upload_data["status"] == "STORED_LOCALLY"
    assert upload_data["mime_type"] == "image/png"
    assert upload_data["sha256"] is not None

    # 2. Retrieve attachment record
    get_att = client.get(f"/api/attachments/{file_id}")
    assert get_att.status_code == 200
    assert get_att.json()["file_id"] == file_id

    # 3. Analyze vision with file_id
    vision_res = client.post("/api/vision/analyze", json={"file_id": file_id})
    assert vision_res.status_code == 200
    v_data = vision_res.json()
    assert v_data["file_id"] == file_id
    assert v_data["status"] == "SUCCESS"
    assert "ONNX Runtime" in v_data["runtime"]
    assert v_data["verification"]["npu_verified"] is False


def test_file_upload_security_rejections(client) -> None:
    # Reject forbidden extension (executable)
    exe_res = client.post(
        "/api/files/upload",
        files={"file": ("malicious.exe", io.BytesIO(b"MZ12345"), "application/octet-stream")},
    )
    assert exe_res.status_code in (400, 415)

    # Reject spoofed MIME with mismatched magic bytes
    fake_png = client.post(
        "/api/files/upload",
        files={"file": ("fake.png", io.BytesIO(b"This is not a real PNG image"), "image/png")},
    )
    assert fake_png.status_code == 400
    assert "signature" in fake_png.json()["detail"].lower()

    # Reject empty file
    empty_res = client.post(
        "/api/files/upload",
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
    )
    assert empty_res.status_code == 400


def test_privacy_persistence(client) -> None:
    # Update camera preference
    put_res = client.put("/api/privacy", json={"camera_enabled": True, "retention_days": 30})
    assert put_res.status_code == 200
    assert put_res.json()["camera_enabled"] is True
    assert put_res.json()["retention_days"] == 30

    # Query in a fresh GET request to verify persistence
    get_res = client.get("/api/privacy")
    assert get_res.status_code == 200
    assert get_res.json()["camera_enabled"] is True
    assert get_res.json()["retention_days"] == 30

    # Revert to safe default
    client.put("/api/privacy", json={"camera_enabled": False, "retention_days": 0})


def test_privacy_controls_memory_disable(client) -> None:
    # Disable persistent memory
    put_res = client.put("/api/privacy", json={"memory_enabled": False})
    assert put_res.status_code == 200
    assert put_res.json()["memory_enabled"] is False

    # Attempt to create memory -> should fail with 403
    payload = {
        "title": "Secret Note",
        "content": "Should not be saved when memory is disabled.",
    }
    create_res = client.post("/api/memory", json=payload)
    assert create_res.status_code == 403

    # Re-enable
    client.put("/api/privacy", json={"memory_enabled": True})


def test_delete_all_memories(client) -> None:
    client.post("/api/memory", json={"title": "Test 1", "content": "Content 1"})
    client.post("/api/memory", json={"title": "Test 2", "content": "Content 2"})

    # Reject without confirm=true
    reject_res = client.delete("/api/memory")
    assert reject_res.status_code == 400

    # Purge with confirm=true
    purge_res = client.delete("/api/memory?confirm=true")
    assert purge_res.status_code == 200
    assert purge_res.json()["status"] == "success"

    # Verify list is empty
    list_res = client.get("/api/memory")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 0


def test_benchmark_storage_baseline(client) -> None:
    res = client.post("/api/benchmarks/run")
    assert res.status_code == 200
    data = res.json()
    assert data["model_name"] == "Local Storage I/O Baseline"
    assert data["average_inference_ms"] is not None
    assert data["first_inference_ms"] is not None
