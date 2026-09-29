from __future__ import annotations

import io
import os
import pytest
from PIL import Image, ImageDraw
from pypdf import PdfWriter

from app.ai.ocr.geometry import polygon_to_bbox, sort_reading_order
from app.ai.ocr.ocr_engine import ocr_engine
from app.schemas.ocr import TextRegion


def test_polygon_to_bbox_coordinate_transform():
    # Test 4-point polygon mapping to normalized [0, 1] and pixel coordinates
    polygon = [[50.0, 100.0], [250.0, 100.0], [250.0, 150.0], [50.0, 150.0]]
    bbox = polygon_to_bbox(polygon, image_width=500, image_height=300)

    assert bbox.x_min == 0.1
    assert bbox.y_min == pytest.approx(0.33333, abs=1e-4)
    assert bbox.x_max == 0.5
    assert bbox.y_max == 0.5
    assert bbox.x_abs_min == 50.0
    assert bbox.y_abs_min == 100.0
    assert bbox.x_abs_max == 250.0
    assert bbox.y_abs_max == 150.0

    # Test clamping beyond image boundaries
    out_of_bounds_poly = [[-20.0, -10.0], [600.0, -10.0], [600.0, 400.0], [-20.0, 400.0]]
    clamped_bbox = polygon_to_bbox(out_of_bounds_poly, image_width=500, image_height=300)
    assert clamped_bbox.x_min == 0.0
    assert clamped_bbox.y_min == 0.0
    assert clamped_bbox.x_max == 1.0
    assert clamped_bbox.y_max == 1.0


def test_sort_reading_order_deterministic():
    # Setup regions out of order:
    # Line 2 right ("WORLD"), Line 1 left ("TITLE"), Line 2 left ("HELLO"), Line 1 right ("NOTE")
    r_title = {"id": "1", "text": "TITLE", "bbox": polygon_to_bbox([[10, 20], [100, 20], [100, 40], [10, 40]], 500, 500)}
    r_note = {"id": "2", "text": "NOTE", "bbox": polygon_to_bbox([[200, 22], [300, 22], [300, 42], [200, 42]], 500, 500)}
    r_world = {"id": "3", "text": "WORLD", "bbox": polygon_to_bbox([[180, 80], [280, 80], [280, 100], [180, 100]], 500, 500)}
    r_hello = {"id": "4", "text": "HELLO", "bbox": polygon_to_bbox([[20, 82], [120, 82], [120, 102], [20, 102]], 500, 500)}

    ordered = sort_reading_order([r_world, r_title, r_hello, r_note])
    ordered_texts = [r["text"] for r in ordered]

    assert ordered_texts == ["TITLE", "NOTE", "HELLO", "WORLD"]
    assert [r["reading_order"] for r in ordered] == [1, 2, 3, 4]


def test_ocr_engine_live_execution():
    # Generate clean image with readable test text
    img = Image.new("RGB", (500, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((25, 30), "SENTINEL ESP32 10k", fill=(0, 0, 0))

    result = ocr_engine.process_image(img, confidence_threshold=0.1)
    assert result.status == "READY"
    assert result.region_count >= 1
    assert any("ESP32" in r.text or "SENTINEL" in r.text for r in result.regions)
    assert result.timing is not None
    assert result.timing.detector_ms > 0
    assert result.timing.recognizer_ms > 0
    assert result.timing.total_ms > 0
    assert result.execution_provider == "CPUExecutionProvider"
    assert result.npu_verified is False


def test_ocr_analyze_and_status_api(client):
    # Create test image and upload attachment
    img = Image.new("RGB", (400, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "WORKSPACE DIAGRAM", fill=(0, 0, 0))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    upload_res = client.post(
        "/api/vision/upload",
        files={"file": ("ocr_test_img.png", buf, "image/png")},
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["file_id"]

    # 1. OCR Analyze API
    analyze_res = client.post(
        "/api/ocr/analyze",
        json={"file_id": file_id, "confidence_threshold": 0.1},
    )
    assert analyze_res.status_code == 200
    data = analyze_res.json()
    assert data["status"] == "READY"
    assert data["region_count"] >= 1
    assert "DIAGRAM" in data["full_text"] or "WORKSPACE" in data["full_text"]
    assert data["execution_provider"] == "CPUExecutionProvider"
    assert data["npu_verified"] is False

    # 2. OCR Status API
    status_res = client.get("/api/ocr/status")
    assert status_res.status_code == 200
    st = status_res.json()
    assert st["is_available"] is True
    assert st["is_loaded"] is True
    assert "EasyOCR" in st["model_name"]
    assert "CRAFT" in st["detector"]
    assert "CRNN" in st["recognizer"]

    # 3. OCR Benchmark API
    bench_res = client.post("/api/ocr/benchmark", params={"file_id": file_id, "warmup": 1, "runs": 2})
    assert bench_res.status_code == 200
    bench_data = bench_res.json()
    assert bench_data["model_name"].startswith("EasyOCR")
    assert bench_data["average_inference_ms"] > 0


def test_document_ingestion_text_file(client):
    # Upload plain text file
    txt_content = (
        "Project: Desk Monitor\n"
        "Sensor: DHT11 temperature and humidity sensor\n"
        "Microcontroller: ESP32-WROOM\n"
        "Pull-up Resistor: 10k ohm connected between VCC and DATA pin.\n"
    )
    buf = io.BytesIO(txt_content.encode("utf-8"))

    upload_res = client.post(
        "/api/files/upload",
        files={"file": ("project_schematic.txt", buf, "text/plain")},
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["file_id"]

    # Ingest document
    doc_res = client.post("/api/documents", json={"file_id": file_id})
    assert doc_res.status_code == 201
    doc = doc_res.json()
    assert doc["source_type"] == "text_file"
    assert doc["status"] == "READY"
    assert doc["page_count"] >= 1
    assert "ESP32-WROOM" in doc["extracted_text"]
    assert doc["extraction_method"] == "direct_text_extraction"
    doc_id = doc["document_id"]

    # Test pages API
    pages_res = client.get(f"/api/documents/{doc_id}/pages")
    assert pages_res.status_code == 200
    pages = pages_res.json()
    assert len(pages) == doc["page_count"]
    assert "10k ohm" in pages[0]["text"]

    # Test text API
    text_res = client.get(f"/api/documents/{doc_id}/text")
    assert text_res.status_code == 200
    assert "DHT11" in text_res.json()["text"]


def test_document_ingestion_native_pdf(client):
    # Generate a pure text-native PDF using pypdf
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)

    # pypdf doesn't easily render text directly without ReportLab,
    # but we can create a clean minimal PDF with text content stream
    stream = b"BT /F1 12 Tf 50 700 Td (Microchip ATmega328P Pinout Specifications) Tj ET"
    # Write stream
    from pypdf.generic import DecodedStreamObject, NameObject, DictionaryObject, ArrayObject, NumberObject
    stream_dict = DecodedStreamObject()
    stream_dict.set_data(stream)
    stream_dict[NameObject("/Length")] = NumberObject(len(stream))
    
    font_dict = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    resources = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_dict}),
    })

    writer.pages[0][NameObject("/Contents")] = stream_dict
    writer.pages[0][NameObject("/Resources")] = resources

    pdf_buf = io.BytesIO()
    writer.write(pdf_buf)
    pdf_buf.seek(0)

    upload_res = client.post(
        "/api/files/upload",
        files={"file": ("atmega328p_specs.pdf", pdf_buf, "application/pdf")},
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["file_id"]

    doc_res = client.post("/api/documents", json={"file_id": file_id})
    assert doc_res.status_code == 201
    doc = doc_res.json()
    assert doc["source_type"] == "pdf_text"
    assert doc["page_count"] == 1
    assert "ATmega328P" in doc["extracted_text"]
    assert doc["ocr_pages_count"] == 0  # Native text does NOT unnecessarily run OCR!


def test_document_search_and_deletion(client):
    # Ingest document with unique search keyword
    txt = "ESP8266 Wi-Fi Module operates on 3.3V logic level. Never supply 5V to GPIO0."
    buf = io.BytesIO(txt.encode("utf-8"))
    upload_res = client.post(
        "/api/files/upload",
        files={"file": ("esp8266_warning.txt", buf, "text/plain")},
    )
    file_id = upload_res.json()["file_id"]
    doc = client.post("/api/documents", json={"file_id": file_id}).json()
    doc_id = doc["document_id"]

    # 1. Search for keyword "GPIO0"
    search_res = client.get("/api/search/documents", params={"q": "GPIO0"})
    assert search_res.status_code == 200
    data = search_res.json()
    assert data["total_hits"] >= 1
    hit = data["results"][0]
    assert hit["document_id"] == doc_id
    assert hit["file_name"] == "esp8266_warning.txt"
    assert "GPIO0" in hit["snippet"]
    assert hit["page_number"] == 1

    # 2. Search for non-existent keyword
    search_empty = client.get("/api/search/documents", params={"q": "NON_EXISTENT_XYZ_TERM"})
    assert search_empty.status_code == 200
    assert search_empty.json()["total_hits"] == 0

    # 3. Delete Document
    del_res = client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "DELETED"

    # Verify document is gone from DB
    get_res = client.get(f"/api/documents/{doc_id}")
    assert get_res.status_code == 404
