# SENTINEL Document Intelligence & Local OCR Architecture

SENTINEL's Document Intelligence pipeline provides a local-first bridge between visual feeds and semantic memory. It extracts readable text from workspace images, notes, datasheets, and circuit diagrams locally on-device using EasyOCR (verified on host CPU) with no cloud OCR dependencies.

---

## 1. Supported Document Formats

| Format | Classification | Extraction Engine | OCR Invoked? |
| :--- | :--- | :--- | :--- |
| **`.txt`, `.md`, `.csv`** | Plain Text Document | Direct UTF-8 Parser | Never |
| **`.pdf` (Text-Native)** | Structured Vector Document | `pypdf` Native Extractor | Never (Zero OCR latency) |
| **`.pdf` (Scanned / Image)** | Rasterized Document | `pypdfium2` Page Renderer + EasyOCR | Yes (Per-page OCR) |
| **`.png`, `.jpg`, `.jpeg`, `.webp`** | Workspace Image / Diagram | EasyOCR CRAFT + CRNN | Yes |

---

## 2. Ingestion Pipeline Architecture

```
Uploaded Document / Image
       │
       ▼
MIME & Header Detection
       │
   ┌───┴──────────────────────────────┐
   │                                  │
[Text File / Native PDF]       [Scanned PDF / Image]
   │                                  │
Direct Text Extraction         Page Render (`pypdfium2`)
   │                                  │
   │                           CRAFT Text Detection
   │                                  │
   │                           CRNN Text Recognition
   │                                  │
   │                           Deterministic Reading Order
   │                                  │
   └───────────────┬──────────────────┘
                   ▼
       Structured Page Record
       - `page_number`
       - `text_content`
       - `text_regions` (Normalized Bounding Boxes)
       - `extraction_method` (DIRECT | OCR)
       - Stage Latencies (`detector_ms`, `recognizer_ms`)
                   │
                   ▼
         SQLite Local Storage
         & Keyword Search Engine
```

---

## 3. OCR Model Architecture (Qualcomm AI Hub Target)

- **Text Detector**: CRAFT (*Character Region Awareness for Text Detection*) — 20.8M parameters.
- **Text Recognizer**: CRNN (*Convolutional Recurrent Neural Network with CTC loss*) — 3.8M parameters.
- **Hardware Execution**:
  - Development Host: `CPUExecutionProvider` (PyTorch CPU Engine).
  - Target Snapdragon Hardware: QNN Execution Provider on Hexagon NPU via Qualcomm AI Hub Windows jobs.
  - **Truthful Status**: `NPU: NOT VERIFIED` until verified against physical Snapdragon silicon.
- **Reading Order Sorting**: Deterministic spatial line grouping (median height overlap threshold) and left-to-right sorting.

---

## 4. Grounded Source References

Every extracted token and sentence retains its structural source:
- **Image OCR**: `source: "image"`, bounding box coordinates `[x_min, y_min, x_max, y_max]`.
- **Document / PDF**: `source: "document"`, `page_number: N`, bounding box coordinates.
- **Direct Extraction**: `source: "text-extraction"`.

This enables future grounding when SENTINEL answers questions like *"What page was the resistor value on?"* (`temperature-project.pdf`, Page 7).

---

## 5. Separation of Documents & Memory

In SENTINEL, **Document Ingestion and Semantic Memory are strictly decoupled**:
- Uploading a document stores the file in `data/uploads/` and populates `documents` and `document_pages` tables.
- It is **not** automatically copied into `memories`.
- Deleting a document removes its page records and file reference, but does not affect independent memory notes.
- Only explicit promotion or user instructions ("*Remember this circuit schematic*") will save extracted content into persistent memory.

---

## 6. Privacy & Security Safeguards

- **Zero Cloud Leakage**: No requests are made to cloud vision, OpenAI, or remote OCR APIs.
- **Path Traversal Protection**: Uploaded files use cryptographic UUIDs (`uuid.uuid4()`) and are sandboxed in the local data directory.
- **Resource Limits**: Configurable max file size (50MB) and max PDF page limit (100 pages) prevent resource exhaustion.
