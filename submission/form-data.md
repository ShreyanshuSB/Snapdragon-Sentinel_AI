# SENTINEL — Qualcomm Snapdragon AI Challenge Submission Form Fields

This document provides the exact text and file references for filling out the official Qualcomm Snapdragon AI Lab competition entry form.

---

### Form Field 1: Project Title

```
SENTINEL — Privacy-First Local Multimodal AI Companion
```

---

### Form Field 2: Brief Project Description (PDF / DOC / DOCX Upload)

- **Upload file**: `submission/SENTINEL_Brief_Description.pdf`
- **Source markdown**: `docs/final-project-description.md`
- **Plain-text summary** (if a text field is provided on the form):

```
SENTINEL is a privacy-first, local-first multimodal AI companion that sees, reads, hears, remembers, understands, and helps users find information across physical workspaces. Verified core components including YOLO-X vision, EasyOCR, Whisper-Tiny, MiniLM semantic memory, workspace tracking, retrieval, and orchestration execute locally on the Intel development host without cloud AI inference dependencies. A Qualcomm QNN/QAIRT/GenieX runtime path is prepared for Snapdragon X-series deployment. Physical Snapdragon NPU execution and the target Qwen3-VL-4B runtime remain not yet verified on hardware.
```

---

### Form Field 3: GitHub Repository Link

```
https://github.com/ShreyanshuSB/Snapdragon-Sentinel_AI
```

> Ensure all local `.env`, SQLite databases, audio recordings, and model binaries remain excluded via `.gitignore` before publishing. Run `python scripts/verify_installation.py` to confirm the repository is clean and reproducible.

---

### Form Field 4: Short Pitch Presentation (PDF Upload)

- **Upload file**: `submission/SENTINEL_Short_Pitch.pdf`
- File size: ~14 KB, 10 slides

---

### Form Field 5: Short Pitch Presentation (PPTX Upload)

- **Upload file**: `submission/SENTINEL_Short_Pitch.pptx`
- File size: ~46 KB, 10 slides

---

### Form Field 6: Snapdragon Laptop Confirmation

> [!CAUTION]
> **MANDATORY USER ACTION AT SUBMISSION TIME**
>
> You must personally and truthfully verify device ownership before checking this box.
>
> - **Question**: *Do you have access to / own a Qualcomm Snapdragon Copilot+ PC (e.g. Snapdragon X Elite / X Plus Windows 11 laptop)?*
>
> - **Directive**: **Requires truthful user confirmation at submission time.**
>   Check this box **ONLY** if you physically have access to or own a Snapdragon Windows ARM64 device.
>   Do not fabricate device eligibility.

---

### Supplementary Notes

**Cloud AI Statement**: SENTINEL does not use any cloud AI API endpoints. Verified core components (YOLO-X vision, EasyOCR, Whisper-Tiny, MiniLM semantic memory, workspace tracking, and retrieval) execute locally without cloud AI inference dependencies.

**Hardware Truthfulness**: Hardware acceleration status is truthfully documented throughout the application, documentation, and pitch materials. Current host is Intel x86_64. Qualcomm Snapdragon Hexagon NPU execution and the target Qwen3-VL-4B runtime are prepared as deployment paths and await physical on-device verification.

**Reproducibility**: Repository includes `run_sentinel.bat` (one-click Windows launcher), `scripts/verify_installation.py` (pre-flight checker), `.env.example` (complete configuration template), and `docs/ai-models.md` (model download guide). No cloud accounts required after initial model artifact download.
