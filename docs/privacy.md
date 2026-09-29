# SENTINEL Privacy & Security Architecture

## Core Privacy Axioms

### 1. Local-First Processing
- **Camera Stream**: Captured and displayed via browser WebRTC directly on device. Never streamed to external servers.
- **Microphone**: Audio capture is strictly user-toggled and processed on-device.
- **Images & Documents**: Stored locally in `data/uploads/` on the local file system.
- **Memory Store**: Contained in local SQLite database `sentinel.db`.
- **Cloud Fallback**: Kept disabled by default.

### 2. User-Controlled Memory
SENTINEL categorically rejects background, ambient surveillance.
- Persistent memory requires explicit user intent (e.g., clicking "Save to Memory" or issuing "Remember this").
- Users can review every stored memory card, inspect timestamp, source type, and project association.
- Users can edit, selectively delete individual memories, or execute an irreversible full database purge.
- Memory persistence can be disabled globally in Settings; when disabled, the backend strictly rejects save requests with HTTP 403 Forbidden.

### 3. Anti-Surveillance Guarantees
SENTINEL will NOT implement:
- Facial recognition or biometric identity matching.
- Emotion or sentiment surveillance.
- Secret audio or video recording.
- Telemetry profiling or cloud tracking.

### 4. File & Document Ingestion Security
- Allowed MIME types are strictly validated (PNG, JPG, WEBP, PDF, TXT, MD, CSV) with file signature / magic byte inspection.
- Upload sizes are strictly capped with chunked streaming protection to avoid memory exhaustion.
- File names are sanitized and assigned cryptographic nonces to prevent path traversal vulnerabilities.
- **Document & Memory Separation**: Ingested documents and extracted OCR text remain in the local documents repository and are NEVER automatically promoted into permanent memory unless explicitly requested by the user. Deleting a document removes its page records and stored file without corrupting independent memory notes.
- **Zero Cloud OCR**: OCR and PDF text extraction are performed 100% locally on-device. No document text or rendered images are ever dispatched to external cloud vision or translation APIs.

### 5. Multimodal Reasoning Privacy & Prompt Injection Defense (Step 4)
- **Zero Cloud LLM Leakage**: The reasoning pipeline contains zero external HTTP requests to OpenAI, Claude, Gemini, Cohere, or hosted inference endpoints. The entire context stays within device memory.
- **Safe Development Diagnostics**: Context debugging and diagnostics only output metadata (source counts, source types, source IDs, estimated token budgets). Raw user text, sensitive document extracts, and private memory content are NEVER logged to production log files.
- **Strict Read/Answer Sandbox**: The reasoning engine operates in a strict, read-only advisory capacity. It has no tool-use access, no shell execution rights, no file-system write privileges, and no database mutation permissions.
- **Adversarial Prompt Injection Defense**: Retrieved documents, OCR text, and user memory cards are treated strictly as untrusted external data. A hardened system prompt explicitly instructs the model to ignore any instructions, prompts, or policy overrides contained within retrieved content.
- **Conversation Persistence Separation**: Conversational chat history does not automatically promote into long-term persistent memory. Chat messages are persisted locally in SQLite for conversational continuity, while long-term memory remains strictly under direct user curation.

### 6. Workspace Tracking & Camera Privacy Guarantees (Step 5)
- **User-Controlled Camera Lifecycle**: Workspace tracking runs ONLY while the user explicitly starts camera capture. Leaving the page or toggling off camera triggers an immediate `STOPPING` command, releasing the MediaStream tracks and clearing all active tracking state.
- **Zero Raw Frame Persistence**: Raw video frames are analyzed entirely in volatile RAM. No live video frames or continuous capture histories are written to disk or the SQLite database.
- **No Facial or Biometric Tracking**: Tracking IDs (`track_001`, `track_002`) represent temporary visual bounding boxes for inanimate workspace objects (bottles, keyboards, laptops, books). Human faces, emotions, and biometric identities are never tracked, labeled, or recorded.
- **Spatial Memory Expiration (TTL)**: Workspace observations automatically transition from `CURRENT_VISIBLE` to `RECENTLY_SEEN`, `STALE`, and are permanently `EXPIRED` within 60 seconds of disappearance.
- **Separate Spatial and User Memory**: Spatial observations do not automatically write into permanent `MEMORA` knowledge cards. Only when a user explicitly assigns a label or notes a finding is a persistent memory created.

### 7. Audio & Voice Privacy Guarantees (Step 6)
- **Default State Microphone OFF**: SENTINEL never listens ambiently or passively in the background. The microphone is strictly `IDLE` until the user explicitly initiates a recording via push-to-talk or click-to-record.
- **Explicit Lifecycle Boundaries**: Microphone capture follows a deterministic state machine: `IDLE` → `REQUESTING_PERMISSION` → `READY` → `RECORDING` → `PROCESSING` → `TRANSCRIBED` → `IDLE`.
- **Hardware Resource Release**: When recording stops or the voice modal closes, all browser `MediaStreamTrack` audio tracks are immediately and cleanly stopped (`track.stop()`), releasing OS microphone access.
- **Bounded Recording Window**: Audio capture is hard-clamped to `MAX_RECORDING_SECONDS = 30.0` seconds to prevent accidental runaway recording if the user leaves their desk.
- **User-Controlled Memory Commits**: Spoken commands ("remember this as...") require explicit spoken intent and an identified target object. Ambient or incidental conversation is never parsed into permanent memory.

### 8. Full Multimodal Orchestration Privacy & Grounding Safety (Step 7)
- **Zero Raw Multimodal Persistence**: Normalization of text, voice transcripts, camera tracks, and document context occurs purely in volatile RAM during query synthesis. No unencrypted multi-modal logs or raw media streams are persisted to disk.
- **Strict Grounding Action Enum**: Grounding actions strictly conform to the `GroundingActionType` enum (`HIGHLIGHT_OBJECT`, `OPEN_DOCUMENT`, `OPEN_MEMORY`, `OPEN_VISION`, `NONE`). The orchestrator never requests or executes arbitrary JavaScript, Python, or shell code from reasoning engine output.
- **Hallucination & Citation Rejection**: `ResponseValidator` strictly validates object presence against active vision tracks before rendering location claims, and strips hallucinated bracket citation tags that do not exist in active context.
- **Truthful Hardware Reporting**: Hardware execution status is never falsified. Development host (Intel x86_64) truthfully reports `CPUExecutionProvider` and `NOT VERIFIED` for NPU acceleration.
- **Sandboxed DEMO MODE**: Deterministic demo fixtures (`DEMO / SIMULATION`) operate in a read-only simulated environment without accessing or mutating live camera feeds, microphone streams, or local user files.

