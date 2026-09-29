# SENTINEL — Final Truth Table

**Single source of truth for all competition submission claims.**  
**Last verified**: 2026-09-30 | **Host**: Intel Core i5-12450H (x86_64, Windows 11)

> [!IMPORTANT]
> Any claim in the pitch, brief, README, or UI that is not listed as **VERIFIED ON HOST** or **PHYSICAL SNAPDRAGON VERIFIED** must be labeled as **TARGET / STAGED** or **PENDING HARDWARE VALIDATION**.

---

## Component Verification Status

| Component | Model / Engine | Current Status | Evidence | Safe Wording |
|---|---|---|---|---|
| **Object Detection** | YOLO-X Small ONNX | ✅ VERIFIED ON HOST | `scripts/benchmark_vision_baseline.py`, ONNX Runtime CPU | "YOLO-X: 88.34 ms on Intel CPU" |
| **Document OCR** | EasyOCR (CRAFT + CRNN) | ✅ VERIFIED ON HOST | `test_ocr_and_documents.py`, live pipeline | "EasyOCR: ~380 ms on Intel CPU" |
| **Speech-to-Text** | Whisper-Tiny (PyTorch FP32) | ✅ VERIFIED ON HOST | `scripts/benchmark_voice.py`, RTF measured | "Whisper-Tiny: RTF 0.264 on Intel CPU" |
| **Semantic Embeddings** | all-MiniLM-L6-v2 (384-d) | ✅ VERIFIED ON HOST | `test_memory.py`, live query | "MiniLM: 7.89 ms query on Intel CPU" |
| **Desk Tracking** | Deterministic IoU/EMA tracker | ✅ VERIFIED ON HOST | `test_workspace_tracking.py`, 9-zone logic | "Deterministic tracker, host CPU" |
| **Find It Localization** | FindItService (Python) | ✅ VERIFIED ON HOST | `test_find_it.py`, TTL state machine | "FindIt: host CPU, deterministic" |
| **Multimodal Orchestration** | SentinelOrchestrator | ✅ VERIFIED ON HOST | `test_sentinel_orchestrator.py`, 145 tests | "Orchestrator overhead: 26.2 ms, host CPU" |
| **VLM Reasoning** | Qwen3-VL-4B-Instruct | ⚠️ TARGET / STAGED | Adapter written; host RAM insufficient | "VLM: Snapdragon GenieX target; NOT on host" |
| **Snapdragon QNN Runtime** | QNNRuntimeAdapter | ⚠️ TARGET / STAGED | Adapter class exists; no Snapdragon hardware | "QNN runtime adapter prepared, not executed" |
| **Snapdragon NPU** | Qualcomm Hexagon NPU | ❌ NOT VERIFIED | No Snapdragon hardware available | "NPU: NOT VERIFIED — pending hardware" |

---

## Performance Claims

| Metric | Value | Hardware | Runtime | What Was Measured | Safe? |
|---|---|---|---|---|---|
| YOLO-X inference | **88.34 ms** | Intel i5-12450H | CPUExecutionProvider | Single-pass ONNX inference (steady-state) | ✅ |
| YOLO-X FPS | **11.32 FPS** | Intel i5-12450H | CPUExecutionProvider | Theoretical throughput (1000/88.34) | ✅ (labeled as theoretical) |
| EasyOCR pipeline | **~380 ms** | Intel i5-12450H | PyTorch CPU | Full CRAFT+CRNN pipeline, warm | ✅ |
| Whisper inference | **792.9 ms** | Intel i5-12450H | PyTorch FP32 CPU | 3.0s audio, warm pass | ✅ |
| Whisper RTF | **0.264** | Intel i5-12450H | PyTorch FP32 CPU | 792.9ms / 3000ms | ✅ |
| MiniLM query | **7.89 ms** | Intel i5-12450H | PyTorch CPU | Single query embedding | ✅ |
| MiniLM batch | **273.1 items/sec** | Intel i5-12450H | PyTorch CPU | Batch throughput test | ✅ |
| Orchestrator overhead | **26.2 ms** | Intel i5-12450H | Python/FastAPI | Evidence collection + action derivation | ✅ |
| Any Snapdragon metric | — | — | — | — | ❌ NONE — not measured |

---

## Privacy Claims

| Claim | Implementation | Status | Verification |
|---|---|---|---|
| No cloud AI APIs | Zero `requests` calls to external AI endpoints | ✅ VERIFIED | Secret scan: 0 cloud API calls |
| Microphone OFF by default | `MediaStreamTrack.stop()` on release; `IDLE` state default | ✅ VERIFIED | Code audit (`VoiceAssistantModal.tsx`) |
| Camera OFF by default | Camera disabled until user clicks Start | ✅ VERIFIED | Code audit (`vision/page.tsx`) |
| No raw audio to disk | Audio processed in RAM, `del audio_arr` after transcription | ✅ VERIFIED | Code audit (`speech/engine.py`) |
| No raw video to disk | Frames decoded in memory, not persisted by default | ✅ VERIFIED | Code audit (`vision/inference_engine.py`) |
| No facial recognition | YOLO-X classes exclude person identity; no face model loaded | ✅ VERIFIED | Model class list audit |
| User-curated memory | Memory saved only on explicit API call with user intent | ✅ VERIFIED | `test_memory.py` |

---

## Model / License Claims

| Model | Artifact ID | Repository License | Artifact License | Safe Wording |
|---|---|---|---|---|
| YOLO-X Small | `Megvii-BaseDetection/YOLOX` | Apache-2.0 | Apache-2.0 | "Apache-2.0" |
| EasyOCR CRAFT | `JaidedAI/EasyOCR` | Apache-2.0 | Apache-2.0 | "Apache-2.0 (repository)" |
| EasyOCR CRNN | `JaidedAI/EasyOCR` | Apache-2.0 | Apache-2.0 | "Apache-2.0 (repository)" |
| Whisper-Tiny | `openai/whisper-tiny` | MIT (upstream repo) | Apache-2.0 (HF artifact metadata) | "MIT (upstream) / Apache-2.0 (HF artifact)" |
| MiniLM-L6-v2 | `sentence-transformers/all-MiniLM-L6-v2` | Apache-2.0 | Apache-2.0 | "Apache-2.0" |
| Qwen3-VL-4B | `Qwen/Qwen3-VL-4B-Instruct` | Apache-2.0 | Apache-2.0 | "Target only — not executed on host" |

---

## Snapdragon Claims

| Claim | Status | Safe Wording |
|---|---|---|
| "Designed for Snapdragon X-series" | ✅ TRUE | Acceptable |
| "QNN/QAIRT/GenieX runtime path" | ✅ TRUE (adapter exists) | Acceptable |
| "CPURuntimeAdapter ↔ QNNRuntimeAdapter" | ✅ TRUE (code exists) | Acceptable |
| "Snapdragon NPU: NOT VERIFIED" | ✅ TRUE (explicitly stated everywhere) | Acceptable |
| "Runs on Snapdragon NPU" | ❌ FALSE | Not acceptable |
| "Verified on Hexagon NPU" | ❌ FALSE | Not acceptable |
| "45 TOPS achieved" | ❌ FALSE | Not acceptable |
| "60 FPS on Snapdragon" | ❌ FALSE | Not acceptable |
| "X ms Snapdragon inference" | ❌ FALSE | Not acceptable |

---

## Demo Mode Claims

| Claim | Status |
|---|---|
| Demo mode uses deterministic fixtures | ✅ TRUE — labeled `[DEMO / SIMULATION]` in UI |
| Demo mode does not imply live camera | ✅ TRUE — clearly labeled |
| Demo mode does not imply Snapdragon execution | ✅ TRUE |
| Live mode uses real YOLO-X + Whisper + MiniLM | ✅ TRUE |
| Live mode uses real Snapdragon NPU | ❌ Not claimed |

---

## Code Quality

| Check | Result | Date |
|---|---|---|
| Backend tests | **145 passed, 0 failed** | 2026-09-30 |
| TypeScript | **0 errors** | 2026-09-30 |
| ESLint | **0 warnings / 0 errors** | 2026-09-30 |
| Production build | **PASS** (8 static routes) | 2026-09-30 |
| Secret scan | **0 API keys / cloud endpoints found** | 2026-09-30 |
