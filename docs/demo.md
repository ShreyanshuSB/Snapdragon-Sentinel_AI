# SENTINEL Canonical Demonstration Script

This document details the official, step-by-step canonical demonstration for SENTINEL (**Steps 1–12**). It establishes the reproducible narrative for live presentations, judge reviews, video walkthroughs, and pitch evaluations.

---

## Demonstration Overview

| Mode | Input Modalities | Capabilities Demonstrated | Target Hardware Profile | Host Runtime Verification |
|---|---|---|---|---|
| **LIVE MODE** | Camera, Microphone, Text | YOLO-X, EasyOCR, STT, Vector Memory, Grounding | Snapdragon X Elite Copilot+ PC | Intel x86_64 CPU (`NOT VERIFIED` for NPU) |
| **DEMO MODE** | Pre-loaded Desk Metadata | Deterministic fallback for conference stages without physical cameras | Snapdragon X Elite Copilot+ PC | Deterministic Local Simulation (`[DEMO / SIMULATION]`) |

---

## Canonical 12-Step Walkthrough

### STEP 1: Launch and Open Vision
- **Action**: Navigate to `http://localhost:3000/vision`.
- **UI State**: The Vision workspace dashboard opens. The status banner reflects `LOCAL • CPU` on Intel staging, or `SNAPDRAGON NPU` on Copilot+ PCs. Privacy indicators display green checkmarks confirming no cloud transmission.
- **Narrative**: *"SENTINEL is your private on-device assistant that sees, reads, remembers, understands, and interacts with your physical workspace without sending a single byte to the cloud."*

### STEP 2: Enable Workspace Desk Tracking
- **Action**: Click the **Start Desk Tracking** button.
- **System Event**: The camera activates locally; YOLO-X (`yolox_s.onnx` / `yolox_tiny.onnx`) begins continuous inference at steady-state frame rates.
- **Privacy Enforcement**: Visual indicator highlights active camera session; no raw frame recording or persistent video disk logging occurs.

### STEP 3: Present Ordinary Desk Objects
- **Action**: Place 3–5 everyday desk objects within the camera field of view:
  1. A water bottle (`center_right`)
  2. A laptop (`center`)
  3. A printed technical note or notebook with visible text (`bottom_left`)
- **System Event**: YOLO-X detects objects and spatial engine assigns normalized bounding coordinates across 9 workspace regions.

### STEP 4: Real-Time Detection & Spatial Tracking
- **UI State**:
  - Colored bounding boxes appear with persistent visual track IDs (`track_001`, `track_002`, `track_003`).
  - EMA temporal smoothing ($\alpha = 0.65$) eliminates bounding-box flicker.
  - OCR overlay recognizes printed text on the notebook: `"Embedded System Firmware Notes"`.
  - Spatial relationships update in real time: `[bottle] is right_of [laptop]`.

### STEP 5: Voice Query — Find It Interaction
- **Action**: Click the microphone icon or tap the Voice Input button on the bottom bar. Speak naturally:
  > *"Where is my water bottle?"*
- **Privacy Enforcement**: Audio stream is captured exclusively in volatile RAM during user hold; no ambient background listening.

### STEP 6: Speech-to-Text Transcription
- **System Event**:
  - Local Whisper-Tiny processes the 16kHz audio stream.
  - Transcription finishes in < 800 ms with Real-Time Factor (RTF) ~0.26x.
  - Transcript appears in the UI search/chat input: `"Where is my water bottle?"`.

### STEP 7: Find It Workspace Localization
- **System Event**:
  - `VoiceRouter` identifies intent `INTENT_FIND_IT`.
  - `find_it_service` matches `"water bottle"` against current active observation state.
  - Resolved track ID: `track_001`, status: `CURRENT_VISIBLE`, region: `center_right`.

### STEP 8: Structured Visual Grounding & Target Highlight
- **UI State**:
  - A glowing pulse animates around `track_001` on the Vision canvas.
  - Grounding Card confirms: `Target: Water Bottle • Region: center_right • Action: HIGHLIGHT_OBJECT`.
  - Assistant responds: *"Your water bottle is visible right now in the center-right area of your desk."*

### STEP 9: Memory Association Query
- **Action**: In the Chat interface or via Voice, ask:
  > *"What did I save about this object?"* (or *"What did I save about my microcontroller notes?"*)
- **Intent**: Semantic memory retrieval linked to current workspace context.

### STEP 10: Local Hybrid Semantic Retrieval
- **System Event**:
  - `MemoryRetriever` executes hybrid vector search using `all-MiniLM-L6-v2` embeddings combined with keyword matching.
  - Returns verified note: `"STM32 firmware flashed via ST-Link on pin 4"`.
  - Assistant provides source attribution chip: `[Memory: Electronics Workshop Notes]`.

### STEP 11: Full Multimodal Grounded Synthesis
- **Action**: Speak or type the grand multimodal question:
  > *"What am I looking at, and what does my saved documentation say about it?"*
- **System Event**:
  - `SentinelOrchestrator` normalizes the multimodal input.
  - Evidence Collector aggregates:
    - **Vision**: Laptop in center, notebook in bottom-left.
    - **OCR**: `"Embedded System Firmware Notes"` on notebook.
    - **Memory**: Saved firmware parameters.
    - **Documents**: Chunks from `microcontroller_guide.pdf`.
  - `ContextBudgetManager` formats strict priority context.
  - `ReasoningEngine` synthesizes grounded response with clear epistemic boundaries.

### STEP 12: Grounded Response Delivery & Grounding Action
- **UI State**:
  - Assistant displays the comprehensive, grounded response:
    - **Observed**: *"I see a laptop in the center and a notebook on the bottom-left with the heading 'Embedded System Firmware Notes'."*
    - **Retrieved**: *"Your saved project documentation notes that the board runs at 3.3V with timer prescalers set to 1MHz."*
    - **Action**: Visual highlighting action illuminates the notebook on camera, with clickable citation chips opening verified source documents.
  - **Verification Badge**: Clearly confirms model identity (`Qwen3-VL Target / Host Staging`) and reports `Snapdragon NPU: NOT VERIFIED` on Intel development host.

---

## Fallback DEMO MODE Walkthrough

When physical desk cameras or specific objects are unavailable (e.g. stage projectors, remote evaluation without peripherals):
1. In the Chat or Settings interface, toggle **Demo Mode**.
2. An explicit badge appears in the navigation bar: `DEMO / SIMULATION`.
3. SENTINEL loads deterministic workspace fixtures (`track_001` bottle, `track_002` laptop, `track_003` notebook) and demo documentation.
4. All 12 interaction steps execute deterministically using simulated local data without claiming live camera or fake NPU execution.
