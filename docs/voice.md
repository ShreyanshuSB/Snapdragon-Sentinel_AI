# Local Voice Engine & Workspace Audio Interaction

## 1. Overview & Purpose

SENTINEL’s Local Voice Engine introduces privacy-first speech recognition and voice-driven workspace localization. Rather than acting as a simple microphone button, the voice engine connects speech to SENTINEL’s existing core capabilities:

$$\text{Voice Input} \longrightarrow \text{Local Whisper STT} \longrightarrow \text{Intent Router} \longrightarrow \begin{cases} \text{Find It (Spatial Grounding)} \\ \text{Workspace Memory (User Aliases)} \\ \text{Document Search} \\ \text{Ask SENTINEL (Multimodal Reasoning)} \end{cases}$$

Every voice turn is executed **100% locally on the user's device** with zero external API calls, zero cloud telemetry, and strict user-controlled audio lifecycles.

---

## 2. Voice Architecture

```
[ Microphone Input (Browser MediaRecorder) ]
                     │ (16kHz Audio Buffer / WAV)
                     ▼
          [ AudioPreprocessor ]
       ├── Format Validation & Resampling
       ├── RMS Silence / Energy Filter
       └── Duration Limit Enforcement (30s max)
                     │ (Normalized 16kHz float32)
                     ▼
             [ SpeechEngine ]
                     │
     ┌───────────────┴───────────────┐
     ▼                               ▼
[ WhisperTransformersAdapter ]  [ SnapdragonWhisperAdapter ]
  • Model: openai/whisper-tiny     • Target: Snapdragon X Elite
  • Runtime: PyTorch CPU           • Runtime: QNNExecutionProvider / QAIRT
  • Device: Host Intel x86_64      • Status: NOT VERIFIED (Target Configured)
  • Status: VERIFIED on Host
                     │
                     ▼ (Structured Transcript: text, duration_ms, RTF)
          [ VoiceActionRouter ]
     ┌───────────────┼───────────────┬───────────────┐
     ▼               ▼               ▼               ▼
[ FindItService ] [ WorkspaceState ] [ DocumentSearch ] [ ChatService ]
• Spatial BBox    • User Alias       • Document Chunks   • Grounded Context
• Spatial Rel.    • Track Binding    • Hybrid Search     • Prompt Defense
```

### Components:
- **`AudioPreprocessor`** (`backend/app/ai/speech/audio_preprocessor.py`):
  Converts arbitrary audio payloads (base64, WAV, PCM) to 16kHz mono float32 arrays, normalizes amplitude to $[-1.0, 1.0]$, applies RMS energy checks to discard silence without running inference, and truncates audio at 30.0 seconds to prevent accidental runaway recordings.
- **`SpeechEngine`** (`backend/app/ai/speech/engine.py`):
  Coordinates preprocessing, adapter execution, real-time factor calculation, and structured response construction.
- **`BaseSpeechAdapter`** (`backend/app/ai/speech/interfaces.py`):
  Standardized abstraction decoupling model weights and execution providers from application logic.
- **`WhisperTransformersAdapter`** (`backend/app/ai/speech/adapter.py`):
  Active development host adapter running `openai/whisper-tiny` locally on CPU.
- **`SnapdragonWhisperAdapter`** (`backend/app/ai/speech/adapter.py`):
  Deployment target adapter for Qualcomm AI Hub Whisper ONNX with `QNNExecutionProvider`. Strictly labeled **NOT VERIFIED** until physical execution on Snapdragon hardware.
- **`VoiceActionRouter`** (`backend/app/ai/speech/router.py`):
  Deterministic intent classifier routing spoken transcripts into:
  - `FIND_IT`: "Where is my water bottle?", "Find the laptop", "Is my phone on the desk?"
  - `REMEMBER_OBJECT`: "Remember this as my multimeter", "Save this object as my notebook"
  - `SEARCH_MEMORY`: "What did I save about Fourier transform?", "Recall my notes"
  - `SEARCH_DOCUMENTS`: "Find the document about microcontrollers"
  - `ASK_SENTINEL`: "What am I looking at?", "What is on the desk?"
  - `GENERAL_QUERY`: General questions routed to multimodal context builder.

---

## 3. Speech Model & Source Information

| Attribute | Host Development Runtime | Snapdragon Target Deployment |
| :--- | :--- | :--- |
| **Model Name** | Whisper-Tiny (Multilingual) | Whisper-Base / Whisper-Tiny |
| **Model Source** | OpenAI / HuggingFace Transformers | Qualcomm AI Hub Reference Model |
| **Official Hub URL** | https://huggingface.co/openai/whisper-tiny | https://aihub.qualcomm.com/compute/models/whisper_base_en |
| **Parameters** | 39 Million | 74 Million (Base) / 39 Million (Tiny) |
| **Format** | PyTorch / Transformers FP32 | ONNX / QNN INT8 (`w8a8`) |
| **Target Hardware** | Intel x86_64 CPU (`CPUExecutionProvider`) | Qualcomm Snapdragon X Elite (Hexagon NPU) |
| **Status** | **VERIFIED ON HOST CPU** | **NOT VERIFIED ON NPU** |
| **License** | MIT License | MIT License |

---

## 4. Microphone Input Lifecycle & Privacy Model

Audio privacy is enforced at every layer:

```
[ IDLE ] ──(User clicks Mic)──> [ REQUESTING_PERMISSION ]
                                          │
                                          ▼
                                      [ READY ]
                                          │
                                          ▼
                                    [ RECORDING ] (Max 30s limit, pulse UI)
                                          │ (User clicks Stop / 30s reached)
                                          ▼
                                   [ PROCESSING ]
                               (Transcribe locally,
                                release MediaStream)
                                          │
                                          ▼
                                  [ TRANSCRIBED ]
                                (Audio discarded)
```

### Privacy Guarantees:
1. **Microphone OFF by Default**: No passive listening or background surveillance. Audio capture occurs only while user actively clicks and holds/records.
2. **Zero Cloud Upload**: Audio never leaves the local machine. Zero requests to OpenAI, Azure, Google Cloud, or third-party speech APIs.
3. **No Raw Audio Persistence**: Raw audio buffers are held in volatile memory only for the duration of feature extraction and are explicitly deleted (`del audio_arr`) immediately upon transcription completion. No audio files are saved to SQLite or disk.
4. **Hardware Release**: MediaStream tracks are explicitly stopped and freed immediately after recording stops.

---

## 5. Voice-to-Action Integration

### A. Find It Voice Flow
1. User clicks Mic: *"Where is my water bottle?"*
2. Whisper transcribes: `"where is my water bottle"`
3. Intent Router identifies `FIND_IT` with query `"water bottle"`.
4. `FindItService` searches active workspace tracks and historical spatial memory.
5. Grounded result returned:
   - Target Track ID: `track_003`
   - Region: `center-right`
   - Confidence: `91%`
   - Relations: `right_of keyboard, near laptop`
6. Frontend highlights the bounding box on the camera canvas with an animated `TARGET FOUND` badge.

### B. Explicit Spoken Memory Flow
1. User clicks Mic: *"Remember this object as my multimeter"*
2. Whisper transcribes: `"remember this object as my multimeter"`
3. Intent Router identifies `REMEMBER_OBJECT` with alias `"my multimeter"`.
4. WorkspaceState binds `"my multimeter"` to the currently visible track ID.
5. System confirms: `"Remembered active object 'multimeter' (track_001) as 'my multimeter'."`

### C. Spoken Document & Memory Search
1. User speaks: *"What did I write about Fourier transform?"*
2. Intent Router directs query to `MemoryService.search_memories`.
3. Returns top grounded memory excerpt with source link.

---

---

## 6. Benchmarks & Performance Telemetry

All benchmarks were measured directly on the host development machine.

### Host Development Benchmark (Measured)
- **Host Hardware**: 12th Gen Intel Core i5-12450H / x86_64 Windows 11
- **Host Execution Provider**: `CPUExecutionProvider` / PyTorch CPU FP32
- **Model Size**: 39M parameters (~151 MB disk footprint)
- **Audio Duration**: 3.0 seconds (16kHz mono)
- **Synthetic Multi-Tone Pipeline Latency**: 1,417 ms (RTF 0.472)
- **Real Speech Benchmark Fixture (`scripts/benchmark_voice.py`)**:
  - **Cold Load Latency**: 1,701 ms
  - **Warm Inference Latency**: **792.9 ms**
  - **Real-Time Factor (RTF)**: **0.2643** (> 3.7x faster than real-time on host CPU)

### Snapdragon Target Reference (Qualcomm AI Hub Specification)
- **Target Hardware**: Qualcomm Snapdragon X Elite Reference Device
- **Target Runtime**: Qualcomm Neural Processing SDK (QNN) / Hexagon NPU INT8
- **AI Hub Reference Latency**: 14.0 ms
- **Reference Real-Time Factor**: $\approx 0.005$ ($> 200\times$ faster than real-time)
- **Verification Status**: **NOT VERIFIED ON PHYSICAL HARDWARE**

---

## 7. Multimodal Sentinel Loop Integration (Step 7)
Voice input seamlessly enters the unified `SentinelOrchestrator` (`backend/app/services/sentinel_orchestrator.py`):
1. **Normalization**: Spoken queries are received with transcript, duration, and confidence metrics.
2. **Intent & Grounding Action**: Voice queries such as *"Where is my keyboard?"* resolve to `HIGHLIGHT_OBJECT` with track IDs and workspace zones.
3. **Multimodal Synthesis**: Full multimodal questions like *"What am I looking at and where did I save information about it?"* combine voice transcripts with live vision tracks, OCR text, and semantic memories in a single grounded response.

---

## 8. Known Limitations
- Current development machine executes Whisper on host CPU; NPU acceleration is architecturally prepared but requires physical Snapdragon hardware for verification.
- Browser audio capture requires user-granted microphone permissions.
- Whisper confidence values are uncalibrated in greedy decoding mode and are truthfully reported as `None` rather than fabricated.
