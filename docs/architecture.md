# SENTINEL System Architecture

## Architecture Diagram

```
+--------------------------------------------------------------------------+
|                       SENTINEL Presentation Layer                        |
|   Next.js 16 (App Router) + React 19 + TypeScript + Tailwind CSS         |
|   Pages: Home | Vision | Documents | Memory | Ask SENTINEL | AI Lab       |
+--------------------------------------------------------------------------+
                                     |
                                     | HTTP / REST (port 8000)
                                     v
+--------------------------------------------------------------------------+
|                     FastAPI Local Backend (Python 3.13)                  |
|                                                                          |
|   API Endpoints:                                                         |
|     /api/health            /api/status            /api/privacy           |
|     /api/memory            /api/memory/search     /api/memory/embed      |
|     /api/memory/reindex    /api/memory/embedding-status                 |
|     /api/projects          /api/chat                                     |
|     /api/vision/analyze    /api/vision/capture    /api/vision/upload     |
|     /api/ocr/analyze       /api/ocr/status        /api/ocr/benchmark     |
|     /api/documents         /api/documents/{id}    /api/search/documents  |
|     /api/workspace/state   /api/workspace/find-it                        |
|     /api/speech/transcribe /api/speech/status     /api/speech/benchmark  |
|     /api/system/hardware   /api/system/runtime    /api/system/diagnostics|
|     /api/models/candidates /api/models/selection  /api/models/status     |
|                                                                          |
|   Services Layer:                                                        |
|     HardwareDiagnostics    RuntimeDiagnostics     EnvironmentReport      |
|     MemoryService          ProjectService         PrivacyService         |
|     ChatService            VisionService          BenchmarkService       |
|     OCRService             DocumentService        DocumentParser         |
|     MemoryIndexer          MemoryRetriever        FindItService          |
|     SpeechService          VoiceActionRouter      WorkspaceState         |
+--------------------------------------------------------------------------+
          |                      |                     |                     |
          | Vision Pipeline      | OCR Pipeline        | Memory/Retrieval    | Speech Pipeline
          v                      v                     v                     v
+----------------------+ +--------------------+ +-------------------------+ +---------------------+
| Vision Engine        | | OCR Engine         | | Embedding Engine        | | Speech Engine       |
| - InferenceEngine    | | - OCREngine        | | - EmbeddingEngine       | | - SpeechEngine      |
| - YOLO-X Adapter     | | - EasyOCR Adapter  | | - ModelAdapter:         | | - Whisper Adapter   |
| - ONNX Runtime       | |   (CRAFT + CRNN)   | |   • NomicEmbedText (QNN)| |   (Tiny / Base)     |
| - Execution Provider | | - Geometry/Reading | |   • SentenceTransformer | | - AudioPreprocessor |
|   State Machine      | |   Order Sorter     | | - RuntimeAdapter:       | | - Intent Router     |
|                      | |                    | |   • CPURuntimeAdapter   | |   (FindIt / Memory) |
|                      | |                    | |   • QNNRuntimeAdapter   | |                     |
+----------------------+ +--------------------+ +-------------------------+ +---------------------+
                                                       |
                                                       v
                                                +-------------------------+
                                                | Local SQLite Database   |
                                                | - memories (+ BLOB vec) |
                                                | - document_chunks (+vec)|
                                                | - projects              |
                                                | - documents             |
                                                | - document_pages        |
                                                +-------------------------+
          |                      |                     |                     |
          +----------------------+---------------------+---------------------+
                                 |
                                 v
+--------------------------------------------------------------------------+
|                   Hardware Acceleration & Fallback Layer                 |
|   Target: Qualcomm Hexagon NPU via QNN Execution Provider (Snapdragon)   |
|   Fallback: Host Processor via CPU Execution Provider (Dev Machine)      |
+--------------------------------------------------------------------------+
```

## Target AI Pipeline Hierarchy

SENTINEL strictly isolates hardware and runtime specifics from the presentation layer:

```
VisionService 
    ↓ 
InferenceEngine (abstract interface)
    ↓ 
VisionModelAdapter (e.g. YOLO-X pre/post-processing)
    ↓ 
RuntimeAdapter (e.g. ONNX Runtime session manager)
    ↓ 
Execution Provider (QNNExecutionProvider / CPUExecutionProvider)
    ↓ 
Hardware Accelerator (Qualcomm Hexagon NPU / Host CPU)
```

The frontend never directly knows:
- Qualcomm QNN API details
- ONNX Runtime session pointers or tensors
- Model-specific bounding box layouts or normalization logic

### Semantic Memory & Retrieval Pipeline Hierarchy

```
MemoryService / DocumentService
    ↓
EmbeddingEngine (dimension validation, serialization, duplicate detection)
    ↓
EmbeddingModelAdapter (e.g. NomicEmbedTextAdapter, SentenceTransformerEmbeddingAdapter)
    ↓
RuntimeAdapter (e.g. CPURuntimeAdapter, QNNRuntimeAdapter)
    ↓
Execution Provider (CPUExecutionProvider on Host / QNNExecutionProvider on Snapdragon)
    ↓
Hardware Accelerator (Host CPU / Qualcomm Hexagon NPU)
```

The memory and document layers strictly isolate:
- Tensor formats and embedding dimensions
- Direct model library calls
- Quantization details and binary blob vector serialization
- Similarity metric implementations (cosine similarity with numerical safety)

### Multimodal Reasoning Pipeline Hierarchy (Step 4)

```
ConversationService
    ↓
ReasoningEngine (lifecycle, metrics, diagnostic representation)
    ↓
ReasoningModelAdapter (e.g. Qwen3VLModelAdapter, LocalCPUReasoningAdapter)
    ↓
RuntimeAdapter (e.g. GenieXRuntimeAdapter, CPURuntimeAdapter)
    ↓
Execution Provider (QAIRT / GenieX on Snapdragon / CPU fallback on Host)
    ↓
Hardware Accelerator (Qualcomm Hexagon NPU / Host CPU)
```

The conversational and reasoning interfaces strictly isolate:
- Qwen tokenization and multimodal tensor layouts
- Qualcomm GenieX and QAIRT C/C++ engine APIs
- Retrieval mechanics (semantic memory and document chunks are retrieved externally)
- Context budget pruning and prompt injection barriers
- Citation validation and response structuring

### Workspace Tracking & Find It Hierarchy (Step 5)

```
VisionEngine (YOLO-X Detections)
    ↓
ObjectTracker (IoU + Centroid Distance + EMA Temporal Smoothing)
    ↓
SpatialReasoningEngine (9 Normalized Zones + Relative Deterministic Geometry)
    ↓
WorkspaceState / SpatialMemory (Active Tracks + TTL Observation Expiration)
    ↓
FindItService (Hierarchical Resolution + Uncertainty & Ambiguity States)
    ↓
Visual Grounding Layer (UI Animated Target Highlight + Context Grounding)
```

The workspace tracking system strictly isolates:
- Raw video stream frames from database persistence
- Temporary visual track IDs (`track_001`, `track_002`) from permanent human user memory
- Geometric coordinate computations from probabilistic model inferences

### Speech & Voice Engine Hierarchy (Step 6)

```
Microphone Capture (User Click-to-Record / Hold-to-Talk)
    ↓
AudioPreprocessor (16 kHz Resampling, Mono Conversion, Normalization, RMS Silence Filter)
    ↓
SpeechEngine (Session Management, Buffer Lifecycle, Latency & RTF Telemetry)
    ↓
SpeechModelAdapter:
    • WhisperTransformersAdapter (Local FP32 CPU on Development Host)
    • SnapdragonWhisperAdapter (Qualcomm QNN Hexagon NPU Target)
    • MockSpeechAdapter (Deterministic CI Architecture Tests)
    ↓
VoiceActionRouter (Regex Intent Extraction & Service Delegation):
    • FIND_IT → FindItService
    • REMEMBER_OBJECT → WorkspaceState.remember_object
    • SEARCH_DOCUMENTS → DocumentService.search_documents
    • SEARCH_MEMORY → MemoryService.search_memories
    • ASK_SENTINEL → ConversationService
    ↓
Grounded UI Presentation & Context Grounding
```

The speech and voice subsystem strictly isolates:
- Audio capture and media hardware control from business reasoning logic
- Model acoustic decoding from conversational chat pipelines
- In-memory ephemeral audio buffers from permanent database storage
- Natural language intent extraction from domain-specific service implementations

### Unified Multimodal Loop: SentinelOrchestrator (Step 7)

```
USER INPUT (Text / Voice / Image / Document / Workspace)
    ↓
Input Normalization (Modality Harmonization, Mode Verification)
    ↓
Dynamic Evidence Collection:
    • Vision: YOLO-X Tracked Desk Objects + Bounding Boxes + Regions
    • OCR: CRAFT + CRNN Associated Text Snippets
    • Memory: Hybrid Semantic/Lexical Vector Hits (MiniLM)
    • Documents: Ingested Technical Document Chunks (PDF/TXT)
    • Tracking: Active Workspace State & Recent Observations
    ↓
Context Hierarchy & Priority Budgeting (Strict Token Management)
    ↓
Local Multimodal Reasoning Engine (Qwen3-VL Target Architecture)
    ↓
ResponseValidator (Fact-Checking, Epistemic Tiering, Citation Sanitization)
    ↓
Grounding Action Resolution (HIGHLIGHT_OBJECT, OPEN_DOCUMENT, OPEN_MEMORY)
    ↓
Interactive Grounded Response Delivery & Viewport Animation
```

The unified orchestration layer strictly enforces:
- Modality-agnostic query normalization without raw media persistence
- Separation between observed physical facts, retrieved notes, and speculative inferences
- Rejection of invented locations or invalid source citations
- Deterministic, typed UI actions (`GroundingActionType` enum) without arbitrary code execution

## Key Architectural Principles

1. **Decoupled Model Layer**:
   The presentation and service layers never invoke specific model libraries directly. All interactions route through typed interfaces (`VisionEngine`, `InferenceEngine`, `VisionModelAdapter`), allowing models to be updated without altering frontend components.

2. **Decoupled Hardware Execution**:
   Inference runtimes (ONNX Runtime, Qualcomm QNN) are encapsulated behind adapter boundaries. Switching execution from CPU to Hexagon NPU is managed through the execution provider state machine without altering application logic.

3. **Strict Truthfulness**:
   Hardware detection is not conflated with hardware execution verification. A detected NPU remains `npu_execution_verified: false` until a real model benchmark has proven execution on the physical accelerator.

4. **Target Profile Separation**:
   Development hosts (x86_64 Intel/AMD workstations) are strictly identified as staging environments. The production profile targets Qualcomm Snapdragon Copilot+ hardware.

5. **Local Data Persistence**:
   All user files, captures, and database entries are stored locally within the user workspace. Zero network or cloud dependencies are required.
