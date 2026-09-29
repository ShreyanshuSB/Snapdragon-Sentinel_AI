# SENTINEL — Official 3-Minute Competition Demonstration Script
**Project**: SENTINEL — Privacy-First Local Multimodal AI Companion  
**Target Platform**: Qualcomm Snapdragon Copilot+ PC (Windows 11 ARM64)  
**Presenter Tone**: Confident, technically precise, grounded, zero exaggeration.

---

### Timing Breakdown
- **0:00 – 0:30**: Introduction & The Problem (Why Local AI for Desks?)
- **0:30 – 1:15**: Live Vision & Spatial Desk Tracking
- **1:15 – 2:00**: Hands-Free Voice Query & "Find It" Visual Grounding
- **2:00 – 2:40**: Local Multimodal Synthesis & Grounded Evidence
- **2:40 – 3:00**: Snapdragon Architecture, Technical Validation & Wrap-up

---

### [0:00 – 0:30] Introduction & The Problem
> **Presenter**:  
> *"Good morning. This is SENTINEL: your privacy-first, local-first multimodal companion that sees, reads, hears, remembers, understands, and finds items in your physical workspace.*
> 
> *Today, AI assistants are severely fragmented. Cloud chat models cannot see your physical desk. Vision models don't remember your notes. More critically, streaming live desk cameras, proprietary hardware schematics, or continuous room audio into cloud APIs can create significant privacy risks and network latency — problems SENTINEL is designed to avoid.
> 
> *SENTINEL is designed specifically for Qualcomm Snapdragon Copilot+ PCs, keeping core AI on-device."*

---

### [0:30 – 1:15] Live Vision & Spatial Desk Tracking
> **Presenter Action**:  
> *Navigates to `http://localhost:3000/vision` and clicks **Start Desk Tracking**.*
> 
> **Presenter**:  
> *"First, let's look at the physical workspace. Notice that our camera is OFF by default. When I activate it, real-time local object detection begins immediately.
> 
> On my desk, I have a laptop, a water bottle, and an engineering notebook with printed firmware notes.
> 
> SENTINEL's local YOLO-X model detects each item, while our deterministic tracking engine assigns persistent track IDs (`track_001`, `track_002`) and applies exponential moving average temporal smoothing to eliminate bounding-box jitter. Notice how EasyOCR simultaneously extracts text directly from the notebook. 
> 
> Crucially, zero raw video frames are written to disk or transmitted to the cloud. Everything lives strictly in volatile memory."*

---

### [1:15 – 2:00] Hands-Free Voice Query & "Find It" Visual Grounding
> **Presenter Action**:  
> *Taps the microphone icon on screen.*
> 
> **Presenter Spoken Query**:  
> *"Where is my water bottle?"*
> 
> **Presenter Action**:  
> *Releases microphone button. Whisper-Tiny transcribes the audio in ~790 ms.*
> 
> **Presenter**:  
> *"Notice the instant response. Our local Whisper speech engine decoded the audio in under 800 milliseconds on local CPU—over 3.7 times faster than real-time.
> 
> The Voice Action Router classified the intent as a spatial search query. The 'Find It' service immediately localized the water bottle in the `center_right` area of the desk and issued a structured `HIGHLIGHT_OBJECT` action. 
> 
> Notice the glowing cyan target pulse illuminating the physical bottle on screen. This isn't abstract text; it's genuine physical visual grounding."*

---

### [2:00 – 2:40] Local Multimodal Synthesis & Grounded Evidence
> **Presenter Action**:  
> *Navigates to Ask SENTINEL and asks:*  
> *"What am I looking at, and what did I previously save about this board?"*
> 
> **Presenter**:  
> *"Now we see the full multimodal loop. Our central `SentinelOrchestrator` aggregates live vision tracks, OCR text, and semantic memory vectors.
> 
> Look at the structured answer:
> 1. It directly separates **Observed Facts**—stating that the board and notebook are visible on the desk.
> 2. It attaches **Retrieved Facts**—citing our local SQLite notes and `microcontroller_guide.pdf`.
> 3. Our `ResponseValidator` strictly validates citations against actual database records and rejects any hallucinated locations.
> 
> No cloud API was contacted. Every source is verifiable."*

---

### [2:40 – 3:00] Snapdragon Architecture, Truthful Audit & Wrap-Up
> **Presenter Action**:  
> *Switches to the AI Lab screen (`/ai-lab`).*
> 
> **Presenter**:  
> *"Finally, let's examine technical deployment. 
> 
> SENTINEL's modular runtime adapters are engineered for Qualcomm AI Engine Direct (QNN), Qualcomm Neural Processing SDK (QAIRT), and Qualcomm GenieX on Snapdragon X-series Windows Copilot+ PCs.
> 
> In keeping with strict technical truthfulness: our development host is an Intel workstation. Across all screens and APIs, physical Snapdragon NPU acceleration is reported truthfully as **NOT YET VERIFIED**, awaiting hardware deployment.
> 
> With 145 passing backend tests, clean TypeScript compilation, and zero cloud dependencies, SENTINEL proves that real physical AI can be private, fast, and grounded on device. 
> 
> Thank you."*
