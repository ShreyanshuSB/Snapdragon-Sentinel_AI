# SENTINEL — Privacy-First Local Multimodal AI Companion

> *A privacy-first local multimodal AI companion that sees, reads, hears, remembers, understands, and helps users find information across their workspace.*

**Qualcomm Snapdragon AI Lab Build & Present Challenge — Competition Submission**

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Backend Tests](https://img.shields.io/badge/backend%20tests-145%20passed-brightgreen)](#testing)
[![TypeScript](https://img.shields.io/badge/TypeScript-0%20errors-blue)](#testing)
[![Host](https://img.shields.io/badge/host-Intel%20x86__64-lightgrey)](#snapdragon-deployment)
[![Target](https://img.shields.io/badge/target-Snapdragon%20X--series-red)](#snapdragon-deployment)

---

## Why SENTINEL?

Modern AI assistants force a tradeoff: cloud services offer powerful capabilities but require sending sensitive desk photos, audio recordings, and confidential documents to remote servers. Meanwhile, existing tools are fragmented — vision tools don't remember, chat models cannot see your physical desk hardware, and note-taking systems lack spatial awareness.

SENTINEL is a privacy-first, local-first multimodal AI companion. Verified core perception, speech, memory, retrieval, and workspace capabilities execute locally on the development host without cloud inference dependencies. A Qualcomm QNN/QAIRT/GenieX runtime path is prepared for Snapdragon X-series deployment, with physical NPU validation pending.

---

## Core Capabilities

| Capability | Engine | Status |
|---|---|---|
| **SEE** — Real-time object detection | YOLO-X Small (ONNX) | ✅ Verified on host CPU |
| **READ** — Document OCR & ingestion | EasyOCR (CRAFT + CRNN) | ✅ Verified on host CPU |
| **HEAR** — Local speech-to-text | OpenAI Whisper-Tiny | ✅ Verified on host CPU |
| **REMEMBER** — Semantic memory | MiniLM-L6-v2 + SQLite | ✅ Verified on host CPU |
| **UNDERSTAND** — Multimodal reasoning | SentinelOrchestrator | ✅ Verified on host CPU |
| **FIND** — Spatial workspace localization | FindItService + 9-zone tracker | ✅ Verified on host CPU |

---

## How It Works

```
User Question (text / voice / camera / document)
             ↓
    SentinelOrchestrator
             ↓
┌────────────────────────────────────────────┐
│  Evidence Collection                       │
│  Vision Tracks + OCR Text + Memory + Docs  │
└────────────────────────────────────────────┘
             ↓
    Context Budget Manager
             ↓
    Reasoning Engine (local)
             ↓
    ResponseValidator (epistemic check)
             ↓
  Structured UI Action (HIGHLIGHT_OBJECT /
  OPEN_DOCUMENT / OPEN_MEMORY / grounded text)
```

Verified local components (YOLO-X, EasyOCR, Whisper-Tiny, MiniLM, tracking, retrieval, orchestration) process queries on-device with no cloud AI inference dependencies. The Qualcomm QNN/QAIRT/GenieX runtime adapter is prepared for Snapdragon X-series deployment; physical NPU validation is pending.

---

## Architecture

```
[ Browser / Next.js UI ] ──(REST / WebSocket)──> [ FastAPI Core ]
                                                        │
          ┌──────────────── SentinelOrchestrator ───────┴──────────┐
          │                                                         │
   [VisionEngine]   [OCREngine]   [SpeechEngine]   [MemoryRetriever]
    (YOLO-X)       (CRAFT+CRNN)   (Whisper-Tiny)   (MiniLM+SQLite)
          │                                                         │
          └──────────── Model Runtime Adapter Layer ────────────────┘
                    ┌──────────────────┬──────────────────┐
                    │                  │                  │
           [CPU Fallback]        [QNN Runtime]      [GenieX VLM]
         (dev host active)    (Snapdragon target) (Snapdragon target)
                    │
            [ SQLite Storage ]
         (vectors + memory + docs)
```

### Frontend
- **Next.js 16** (App Router) + **React 19** + **TypeScript** (strict, 0 errors)
- **Tailwind CSS** — dark glassmorphic cockpit design
- Pages: Home, Vision, Documents, Memory, Chat, AI Lab, Settings

### Backend
- **FastAPI** (Python 3.11+) with Pydantic v2 schemas
- **SQLAlchemy** ORM + SQLite 3 (local vector + data storage)
- **ONNX Runtime** with CPU/QNN execution provider abstraction
- Decoupled 4-tier AI adapter architecture (Service → Engine → Adapter → Runtime)

---

## AI Models

| Model | HuggingFace ID | Size | Host License | Use |
|---|---|---|---|---|
| YOLO-X Small | `Megvii-BaseDetection/YOLOX` | ~34 MB | Apache-2.0 | Object detection |
| EasyOCR (CRAFT) | `JaidedAI/EasyOCR` | ~20 MB | Apache-2.0 | Text detection |
| EasyOCR (CRNN) | `JaidedAI/EasyOCR` | ~4 MB | Apache-2.0 | Text recognition |
| Whisper-Tiny | `openai/whisper-tiny` | ~39 MB | Apache-2.0 (artifact) | Speech-to-text |
| MiniLM-L6-v2 | `sentence-transformers/all-MiniLM-L6-v2` | ~23 MB | Apache-2.0 | Semantic embeddings |

See [`docs/ai-models.md`](docs/ai-models.md) for full model provenance, license details, and download paths.

---

## Snapdragon Deployment

> [!IMPORTANT]
> **Truthful Hardware Status**: All benchmarks below are measured on the **Intel x86_64 development host**. Qualcomm Snapdragon NPU execution is **NOT YET VERIFIED** on physical hardware. This is clearly reported across all application interfaces and documentation.

| Platform | Status |
|---|---|
| **Current dev host** | Intel Core i5-12450H (x86_64, Windows 11) |
| **Target platform** | Snapdragon X Elite / X Plus (Windows 11 ARM64) |
| **Target accelerator** | Qualcomm Hexagon NPU (45 TOPS) |
| **Target runtime** | Qualcomm AI Engine Direct (QNN) + QAIRT + GenieX |
| **NPU verification** | **NOT VERIFIED** — awaiting physical Snapdragon hardware |

SENTINEL's modular runtime adapter architecture (`CPURuntimeAdapter` ↔ `QNNRuntimeAdapter`) is designed to swap execution providers without changing application logic. Target VLM: `Qwen3-VL-4B-Instruct` via Qualcomm GenieX.

---

## Privacy

| Guarantee | Implementation |
|---|---|
| No cloud AI APIs | Zero calls to OpenAI, Anthropic, or any remote inference server |
| Microphone OFF by default | Push-to-talk only; hardware stream released immediately after recording |
| Camera user-controlled | Active only while explicitly enabled; releases handles on page exit |
| No raw media persistence | Video frames and audio processed in RAM only; never written to disk |
| No facial recognition | Categorically excluded from object detection scope |
| User-curated memory | Knowledge cards saved only on explicit user command |

---

## Demo

**Canonical 3-minute demo flow** → [`docs/demo-script.md`](docs/demo-script.md)

**Core sequence:**
1. Open Vision → enable desk tracking → YOLO-X detects objects in real time
2. Speak: *"Where is my water bottle?"*
3. Whisper transcribes locally (~790 ms, RTF 0.264)
4. Find It localizes the bottle → animated cyan highlight on camera
5. Ask: *"What am I looking at and what did I save about it?"*
6. Multimodal grounded response with Observed Facts + Retrieved Evidence citations

**Demo Mode** (no camera required): enable via UI switch or `?mode=demo` URL parameter. Clearly labeled `[DEMO / SIMULATION]` throughout.

---

## Setup

### Prerequisites

- **Python 3.11+** (Python 3.13 tested)
- **Node.js v20+** (v24 tested)
- **pip** and **npm** available on PATH

### Step 1 — Clone repository

```powershell
git clone https://github.com/ShreyanshuSB/Snapdragon-Sentinel_AI.git
cd Snapdragon-Sentinel_AI
```

### Step 2 — Create Python virtual environment

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Step 3 — Install backend dependencies

```powershell
pip install -r backend/requirements.txt
```

### Step 4 — Install frontend dependencies

```powershell
cd frontend
npm install
cd ..
```

### Step 5 — Configure environment

```powershell
copy .env.example .env
# Edit .env if needed (defaults work for local development)
```

### Step 6 — Initialize database

```powershell
cd backend
alembic upgrade head
cd ..
```

### Step 7 — Download AI models

Models are downloaded automatically on first use via Hugging Face cache and ONNX Runtime model registry. See [`docs/ai-models.md`](docs/ai-models.md) for manual download paths and expected sizes.

> **Note**: YOLO-X ONNX model (`models/vision/yolox_s.onnx`, ~34 MB) must be placed manually if not already present. See model docs for download source.

### Step 8 — Pre-flight verification

```powershell
python scripts/verify_installation.py
```

---

## Running Locally

### One-click launcher (Windows)

```powershell
.\run_sentinel.bat
```

This script checks prerequisites, copies `.env.example` to `.env` if needed, installs frontend dependencies, and starts both backend and frontend in separate terminal windows.

### Manual launch

**Backend** (from project root):
```powershell
set PYTHONPATH=backend
.venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend** (in a second terminal):
```powershell
cd frontend
npm run dev
```

Open **http://localhost:3000** in your browser.

- API docs: http://localhost:8000/docs
- System diagnostics: http://localhost:8000/api/system/diagnostics

---

## Configuration

Copy `.env.example` to `.env`. Key variables:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./sentinel.db` | SQLite database path |
| `TARGET_PROFILE` | `snapdragon_x_elite` | Deployment target identifier |
| `RUNTIME_PROVIDER` | `CPUExecutionProvider` | Active ONNX execution provider |
| `HOST_PLATFORM` | `Intel x86_64` | Current host description |
| `NPU_VERIFIED` | `false` | Physical NPU verification status |
| `CAMERA_ENABLED` | `false` | Default camera state |
| `MICROPHONE_ENABLED` | `false` | Default microphone state |
| `MEMORY_ENABLED` | `true` | Enable semantic memory engine |
| `LOCAL_AI_MODE` | `local_only` | AI execution mode |
| `CLOUD_FALLBACK` | `false` | Disable all cloud fallbacks |

---

## Testing

```powershell
# Run full backend test suite
.venv\Scripts\pytest backend/tests -v

# TypeScript type-check
cd frontend && npx tsc --noEmit

# ESLint
cd frontend && npm run lint

# Production build validation
cd frontend && npm run build
```

**Current results (verified on Intel host):**

| Check | Result |
|---|---|
| Backend tests | **145 passed, 0 failed** (14.93s) |
| TypeScript | **0 errors** |
| ESLint | **0 warnings / 0 errors** |
| Production build | **✅ PASS** (10 static routes) |

---

## Benchmarks

All measurements are **Intel Core i5-12450H (x86_64) host CPU** — not Snapdragon NPU.

| Metric | Measured Value | Host |
|---|---|---|
| YOLO-X inference | **88.34 ms** (11.32 FPS) | Intel CPU |
| EasyOCR pipeline | **~380 ms** | Intel CPU |
| Whisper-Tiny (3s audio) | **792.9 ms** (RTF = 0.264) | Intel CPU |
| MiniLM query embedding | **7.89 ms** | Intel CPU |
| MiniLM batch throughput | **273.1 items/sec** | Intel CPU |
| Orchestrator overhead | **26.2 ms** | Intel CPU |

Run benchmarks yourself:
```powershell
python scripts/benchmark_vision_baseline.py
python scripts/benchmark_voice.py
```

---

## Repository Structure

```
Snapdragon/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── ai/                 # Vision, OCR, Speech, Memory engines
│   │   ├── core/               # Config, constants
│   │   ├── database/           # SQLAlchemy models & connection
│   │   ├── routers/            # API endpoints
│   │   ├── schemas/            # Pydantic schemas
│   │   └── services/           # Orchestrator, tracking, demo
│   ├── tests/                  # 145-test backend suite
│   └── main.py
├── frontend/                   # Next.js application
│   └── app/                    # Pages: home, vision, chat, memory, docs, ai-lab
├── docs/                       # Full documentation
│   ├── architecture.md
│   ├── ai-models.md
│   ├── privacy.md
│   ├── snapdragon.md
│   ├── demo-script.md
│   ├── benchmarking.md
│   ├── voice.md
│   ├── workspace-tracking.md
│   ├── final-project-description.md
│   └── submission-readiness.md
├── submission/                 # Competition submission artifacts
│   ├── SENTINEL_Short_Pitch.pptx
│   ├── SENTINEL_Short_Pitch.pdf
│   └── form-data.md
├── scripts/                    # Utilities
│   ├── generate_pitch_deck.py
│   ├── verify_installation.py
│   ├── benchmark_vision_baseline.py
│   └── benchmark_voice.py
├── models/                     # AI model weights (gitignored binary files)
│   └── vision/                 # Place yolox_s.onnx here
├── data/                       # Runtime data (gitignored)
├── config/                     # Target profile configuration
├── .env.example                # Environment configuration template
├── run_sentinel.bat            # One-click Windows launcher
├── LICENSE                     # Apache-2.0 (SENTINEL source)
└── THIRD_PARTY_NOTICES.md      # Third-party model attributions
```

---

## Limitations

1. **Host VLM inference**: Full 4B-parameter VLM (`Qwen3-VL-4B-Instruct`) requires dedicated Snapdragon NPU or discrete GPU; adapter is staged for target deployment.
2. **Snapdragon NPU not verified**: Physical NPU execution awaits access to Snapdragon X-series Windows ARM64 hardware. All benchmarks are Intel host CPU measurements.
3. **Lighting sensitivity**: Extreme shadows or glare reduce EasyOCR accuracy on physical desk objects.
4. **Small model limitations**: Whisper-Tiny may misrecognize domain-specific technical terminology.

---

## Model Licenses

| Model | Repository License | Notes |
|---|---|---|
| YOLO-X | Apache-2.0 | Megvii-BaseDetection |
| EasyOCR | Apache-2.0 | JaidedAI |
| Whisper-Tiny | MIT (code) / Apache-2.0 (HF artifact metadata) | See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) |
| MiniLM-L6-v2 | Apache-2.0 | sentence-transformers |

SENTINEL source code is licensed under **Apache-2.0** (see [`LICENSE`](LICENSE)).  
Third-party model attributions: [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

---

## Submission Status

| Deliverable | Status |
|---|---|
| Project title | ✅ SENTINEL — Privacy-First Local Multimodal AI Companion |
| Brief project description | ✅ `docs/final-project-description.md` |
| GitHub repository | ✅ Ready (insert final URL in `submission/form-data.md`) |
| Short pitch PPTX | ✅ `submission/SENTINEL_Short_Pitch.pptx` |
| Short pitch PDF | ✅ `submission/SENTINEL_Short_Pitch.pdf` |
| Demo script | ✅ `docs/demo-script.md` |
| Backend tests | ✅ 145/145 passing |
| TypeScript | ✅ 0 errors |
| Production build | ✅ Pass |
| Snapdragon NPU verification | ⏳ Pending physical hardware access |

---

*SENTINEL is open-source software. See [LICENSE](LICENSE) for terms.*
