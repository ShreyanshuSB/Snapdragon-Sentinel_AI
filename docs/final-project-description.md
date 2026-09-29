# SENTINEL — Privacy-First Local Multimodal AI Companion
**Official Submission Brief | Qualcomm Snapdragon AI Lab Build & Present Challenge**

---

### Executive Summary & One-Line Description
> *"A privacy-first local multimodal AI companion that sees, reads, hears, remembers, understands, and helps users find information across their workspace."*

SENTINEL is a privacy-first, local-first multimodal AI companion designed to keep core perception, speech, memory, retrieval, and interaction processing on-device — eliminating the need to send sensitive workspace data to cloud services. Core components (YOLO-X, EasyOCR, Whisper-Tiny, MiniLM) run and have been verified on the local host CPU. A Qualcomm Snapdragon QNN/QAIRT/GenieX runtime path is prepared for physical hardware validation on Snapdragon X-series Copilot+ PCs.

---

### 1. Problem Statement
Knowledge workers, engineers, hardware designers, and students constantly navigate a disjointed divide between physical desks and digital workspaces:
- **Modality Fragmentation**: Computer vision tools don't remember context; conversational LLMs cannot see physical desk hardware; voice transcription tools lack spatial awareness; and note repositories remain static.
- **Cloud Privacy Risk**: Streaming live desk camera video, proprietary prototype hardware photos, or conversational audio to third-party cloud APIs can pose significant data privacy and compliance risks — particularly for sensitive or proprietary workspace content.
- **Physical Hallucination**: Cloud models without grounded visual context frequently fabricate object coordinates, invent document citations, and present speculative inferences as confirmed facts.
- **Network Latency & Offline Inability**: Cloud-dependent workflows introduce network latency and require connectivity, which limits responsiveness for interactive physical desk localization and prevents offline operation.

---

### 2. The Solution
SENTINEL is a privacy-first, local-first AI companion that coordinates physical workspace perception and local semantic memory into one unified multimodal feedback loop. Verified local components (vision, OCR, speech, semantic memory) run on-device with no external network calls. A Qualcomm Snapdragon QNN/QAIRT/GenieX runtime adapter is prepared for deployment on Snapdragon X-series hardware once physical validation is completed.

---

### 3. Core Workflow
SENTINEL organizes physical intelligence into six tightly coupled stages:

$$\mathbf{SEE} \longrightarrow \mathbf{READ} \longrightarrow \mathbf{HEAR} \longrightarrow \mathbf{REMEMBER} \longrightarrow \mathbf{UNDERSTAND} \longrightarrow \mathbf{FIND}$$

1. **SEE**: Real-time object detection and persistent bounding-box tracking.
2. **READ**: Document and desk OCR text extraction with spatial binding.
3. **HEAR**: Local, on-device speech-to-text with deterministic intent routing.
4. **REMEMBER**: Dense vector embeddings and local hybrid search with project isolation.
5. **UNDERSTAND**: Evidence-aware multimodal reasoning with epistemic fact-checking.
6. **FIND**: Natural-language spatial localization with interactive visual grounding.

---

### 4. Key Capabilities
- **Local Object Detection & Spatial Tracking**: YOLO-X detector integrated with an IoU/centroid tracker, EMA smoothing ($\alpha = 0.65$), and 9 normalized spatial workspace zones.
- **Local Document OCR & Parsing**: EasyOCR (CRAFT + CRNN) and native PDF parsing with deterministic reading order and page-level attribution.
- **Private Voice Engine**: Whisper-Tiny speech-to-text with silencer gating and fast intent routing to Find It, Memory, Documents, or Multimodal Conversation.
- **Local Hybrid Semantic Memory**: Dense 384-dimensional vector embeddings (`all-MiniLM-L6-v2`) combined with lexical scoring and user-controlled metadata curation.
- **Structured Grounding Actions**: Resolves queries into typed UI actions (`HIGHLIGHT_OBJECT`, `OPEN_DOCUMENT`, `OPEN_MEMORY`) rather than generating unverified code.
- **Fact-Checked Epistemic Tiers**: Distinguishes directly *Observed Facts* (camera/OCR) from *Retrieved Facts* (notes/PDFs) and *Inferred Hypotheses*, actively rejecting hallucinated locations.

---

### 5. Privacy & Security by Design
- **Local-First Mandate**: Zero cloud AI APIs (zero dependencies on OpenAI, Anthropic, or external inference servers).
- **Explicit Sensor Control**: Camera and microphone are strictly `OFF` by default. Capture requires explicit user initiation.
- **Zero Raw Media Disk Persistence**: Camera frames and audio streams exist exclusively in volatile RAM buffers. No video streams or audio WAV recordings are persisted to disk or the database.
- **Anti-Surveillance Guarantees**: Categorically rejects facial recognition, biometric profiling, and ambient background listening.
- **User-Curated Memory**: Observations and chat histories never auto-contaminate persistent memory without explicit user confirmation.

---

### 6. Qualcomm Snapdragon Relevance & Architecture
SENTINEL is specifically designed to exploit Qualcomm's Windows on Snapdragon AI ecosystem:
- **Target Platform**: Snapdragon X Elite / Snapdragon X Plus (Windows 11 ARM64).
- **Runtime Stack**: Qualcomm AI Engine Direct (QNN), Qualcomm Neural Processing SDK (QAIRT), and Qualcomm GenieX runtime.
- **Vision Acceleration Target**: YOLO-X quantized to INT8 (w8a8) is the planned execution target on the Qualcomm Hexagon NPU — not yet physically verified on Snapdragon hardware.
- **Speech Acceleration Target**: ONNX DirectML / QNN pipeline prepared for Snapdragon, targeting sub-100ms transcription latency upon hardware validation.
- **Multimodal VLM Target**: Decoupled adapter architecture supporting `Qwen3-VL-4B-Instruct` via Qualcomm GenieX.
- **Current Development Hardware Separation**:
  - *Current Host Workstation*: Intel 12th Gen Core i5-12450H (x86_64, Windows 11).
  - *Physical NPU Verification Status*: **`NOT VERIFIED ON PHYSICAL HARDWARE`** (truthfully disclosed across all interfaces; zero fabricated vendor metrics).

---

### 7. Technical Architecture
```
[ Browser / Next.js UI ] ──(REST / WebSocket)──> [ FastAPI Application Core ]
                                                            │
┌─────────────────────────────── SentinelOrchestrator ──────┴───────────────────────────────┐
│                                                                                           │
│  Input Normalization ──> Evidence Collection ──> Priority Budget ──> Reasoning ──> Action  │
│                                                                                           │
└────────┬──────────────────────┬──────────────────────┬──────────────────────┬─────────────┘
         │                      │                      │                      │
   [ VisionEngine ]      [ EasyOCR Engine ]     [ SpeechEngine ]     [ MemoryRetriever ]
      (YOLO-X)             (CRAFT + CRNN)        (Whisper-Tiny)      (MiniLM + SQLite)
         │                      │                      │                      │
         └──────────────────────┴──────────┬───────────┴──────────────────────┘
                                           │
                               [ Model Runtime Adapters ]
                     ┌─────────────────────┴─────────────────────┐
                     │                                           │
            [ Host CPU Fallback ]                     [ Qualcomm QNN / GenieX ]
          (CPUExecutionProvider)                     (Hexagon NPU - Snapdragon Target)
```

---

### 8. Innovation & Technical Differentiation
1. **Interactive Visual Grounding**: Transforms abstract text responses into physical viewport animations, highlighting target items directly on camera.
2. **Deterministic Response Validation**: `ResponseValidator` strips ungrounded citation tags and flags hallucinated object locations before delivery to the user.
3. **Controlled Stage Demonstration Mode**: Includes deterministic local test fixtures (`[DEMO / SIMULATION]`) enabling reliable presentations even when hardware cameras are restricted.

---

### 9. Empirical Validation & Measured Benchmarks
All metrics reflect real end-to-end execution on the host development workstation:
- **Speech-to-Text (`scripts/benchmark_voice.py`)**:
  - Audio Duration: `3.00 s` (16kHz mono float32)
  - Warm Inference Latency: **`792.9 ms`** on Host CPU
  - Real-Time Factor (RTF): **`0.2643`** (**> 3.7x faster than real-time**)
- **Object Detection (YOLO-X Small)**:
  - Mean Inference Latency: **`88.34 ms`** (11.32 FPS on Host CPU)
- **Document & Text OCR (EasyOCR)**:
  - Total Pipeline Latency: **`~380 ms`**
- **Semantic Vector Retrieval**:
  - Query Embedding: **`7.89 ms`** | Batch Throughput: **`273.1 items/sec`**
- **Orchestration Overhead**:
  - Complete End-to-End Pipeline: **`26.2 ms`** (outside VLM inference)
- **Automated Test Suite**:
  - **145 passed, 0 failed** in `33.70s` across all backend modules.
  - TypeScript: **0 errors** | ESLint: **0 warnings/errors** | Next.js Build: **Clean static bundle**.

---

### 10. Known Limitations
1. **Host VLM Compute**: Full 4B-parameter VLM inference requires dedicated Snapdragon NPU or discrete GPU; currently operates via target adapter staging on host.
2. **Ambient Lighting Sensitivity**: Extreme shadows degrade OCR accuracy on physical objects.
3. **Physical Hardware Gate**: Final NPU deployment requires physical validation on Snapdragon Windows ARM64 hardware.

---

### 11. Reproducibility & Offline Guarantee
- **Zero Cloud Accounts Required**: No OpenAI or third-party API keys.
- **One-Click Windows Launcher**: Automated launch via `run_sentinel.bat`.
- **Pre-Flight Diagnostic Tool**: Automated verification via `python scripts/verify_installation.py`.
- **Offline Operation**: After initial one-time model artifact retrieval, all perception, memory, and orchestration modules function completely offline.
