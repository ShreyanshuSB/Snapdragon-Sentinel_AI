# SENTINEL — Screenshot Checklist

This document specifies the **7 required screenshots** for the competition submission evidence package.  
All screenshots must be captured from the **live running application** (`http://localhost:3000`).  
**Do not fabricate or composite screenshots.**

Save all screenshots to: `submission/assets/`

---

## Setup Before Capturing

1. Run `run_sentinel.bat` (or start backend + frontend manually)
2. Wait for both services to be ready:
   - Backend: `http://localhost:8000/docs` returns 200
   - Frontend: `http://localhost:3000` fully loads
3. Set browser window to **1400 × 900 px** for consistent framing
4. Ensure browser is in **clean state** — no dev tools open, no personal tabs visible, no private documents showing
5. Use **Demo Mode** where indicated (no camera required)

---

## Screenshot Specifications

### 01_home.png

| Field | Value |
|---|---|
| **URL** | `http://localhost:3000` |
| **Mode** | Either Live or Demo |
| **What MUST be visible** | SENTINEL branding, system readiness cards, core capability tiles (SEE / READ / HEAR / REMEMBER / UNDERSTAND / FIND), navigation bar |
| **What MUST NOT be visible** | Debug panels, console errors, personal documents, private data, development terminal |
| **Notes** | Capture the entire viewport; ensure the headline and quick-action cards are fully visible |

---

### 02_vision_tracking.png

| Field | Value |
|---|---|
| **URL** | `http://localhost:3000/vision` |
| **Mode** | Demo Mode or Live with webcam image upload |
| **What MUST be visible** | Object detection bounding boxes, class labels and confidence scores, workspace zone overlay, stage timing metrics (preprocess/inference/postprocess ms), `LOCAL • CPU` badge |
| **What MUST NOT be visible** | `NPU VERIFIED` badge, personal documents in background, private photographs |
| **Notes** | Upload a sample desk image or enable Demo Mode to show detection results |

---

### 03_find_it.png

| Field | Value |
|---|---|
| **URL** | `http://localhost:3000/vision` (Find It tab) |
| **Mode** | Demo Mode recommended |
| **What MUST be visible** | Find It query input, a submitted query (e.g. "Where is my water bottle?"), a grounded/highlighted object result, glowing cyan target indicator on the tracked object |
| **What MUST NOT be visible** | Fake "Snapdragon verified" labels, personal filesystem paths |
| **Notes** | Activate Demo Mode, then use the Find It voice/text query to localize an object |

---

### 04_voice.png

| Field | Value |
|---|---|
| **URL** | Any page with Voice Modal open |
| **Mode** | Voice Modal open (click microphone icon in Navbar) |
| **What MUST be visible** | Voice assistant modal, recording state indicator, transcription result (if captured), `LOCAL • Whisper-Tiny`, `Target: Snapdragon X Elite (NPU NOT VERIFIED)` label, push-to-talk status |
| **What MUST NOT be visible** | Active microphone recording personal audio, private transcribed content |
| **Notes** | Open the voice modal and use the Push-to-Talk button; capture just before or after a sample query |

---

### 05_memory.png

| Field | Value |
|---|---|
| **URL** | `http://localhost:3000/memory` |
| **Mode** | Either Live or Demo |
| **What MUST be visible** | Memory search bar, at least one memory card with source citation, retrieval mode selector (HYBRID / SEMANTIC / KEYWORD), embedding status badge |
| **What MUST NOT be visible** | Private personal notes with confidential content, unrelated personal data |
| **Notes** | Add a sample memory card first if the store is empty; use a neutral example like "MacBook Pro is on the left side of desk" |

---

### 06_multimodal.png

| Field | Value |
|---|---|
| **URL** | `http://localhost:3000/chat` |
| **Mode** | Demo Mode recommended |
| **What MUST be visible** | A multimodal conversation response with source citations (VISION / MEMORY / DOCUMENT tags), structured grounding action badge, evidence card(s), `LOCAL • CPU` processing indicator |
| **What MUST NOT be visible** | Private conversation history, personal documents, fabricated Snapdragon claims |
| **Notes** | Ask a question like "What is on my desk?" in Demo Mode to generate a grounded response with citations |

---

### 07_ai_lab.png

| Field | Value |
|---|---|
| **URL** | `http://localhost:3000/ai-lab` |
| **Mode** | Live (shows real hardware info) |
| **What MUST be visible** | Hardware diagnostics panel showing Intel processor, `HOST CPU ACTIVE • SNAPDRAGON NPU NOT VERIFIED` label, model registry table, execution provider state (`CPUExecutionProvider`), `NOT VERIFIED` Snapdragon badge in amber |
| **What MUST NOT be visible** | Any `VERIFIED` label next to Snapdragon or NPU unless physically verified on hardware |
| **Notes** | This is the most important screenshot for demonstrating hardware truthfulness; make sure the NPU NOT VERIFIED label is clearly readable |

---

## Quick Capture Sequence

```
1. Start app → run_sentinel.bat
2. Open http://localhost:3000     → screenshot → save as 01_home.png
3. /vision (upload test image)   → screenshot → save as 02_vision_tracking.png
4. /vision > Find It tab         → screenshot → save as 03_find_it.png
5. Click mic icon → Voice Modal  → screenshot → save as 04_voice.png
6. /memory (with sample card)    → screenshot → save as 05_memory.png
7. /chat (Demo Mode, ask a Q)    → screenshot → save as 06_multimodal.png
8. /ai-lab                       → screenshot → save as 07_ai_lab.png
```

Total estimated time: **8–12 minutes**

---

## Privacy Checklist Before Uploading

Before using these screenshots in the pitch or GitHub README:

- [ ] No personal documents visible (private PDFs, personal notes)
- [ ] No private photos visible in uploads
- [ ] No filesystem paths visible in any panel
- [ ] No private audio transcriptions visible
- [ ] No secrets, API keys, or tokens visible
- [ ] AI Lab correctly shows `NPU NOT VERIFIED`
- [ ] No `C:\Users\<name>` paths visible in UI
