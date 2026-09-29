#!/usr/bin/env python3
"""
Generates the official competition presentation deck:
- submission/SENTINEL_Short_Pitch.pptx
- submission/SENTINEL_Short_Pitch.pdf
Uses python-pptx and reportlab with high-contrast, dark/cyan visual styling.
"""

from __future__ import annotations

import os
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


ROOT_DIR = Path(__file__).resolve().parent.parent
SUBMISSION_DIR = ROOT_DIR / "submission"
SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)

PPTX_PATH = SUBMISSION_DIR / "SENTINEL_Short_Pitch.pptx"
PDF_PATH = SUBMISSION_DIR / "SENTINEL_Short_Pitch.pdf"

# Design System Palette
BG_COLOR = RGBColor(11, 15, 25)        # Slate 950 (#0B0F19)
CARD_BG = RGBColor(15, 23, 42)        # Slate 900 (#0F172A)
TEXT_WHITE = RGBColor(248, 250, 252)   # Slate 50
TEXT_MUTED = RGBColor(148, 163, 184)   # Slate 400
CYAN_ACCENT = RGBColor(6, 182, 212)    # Cyan 500 (#06B6D4)
AMBER_ACCENT = RGBColor(245, 158, 11)  # Amber 500
GREEN_ACCENT = RGBColor(16, 185, 129)  # Emerald 500


def set_slide_background(slide, color):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_header(slide, title_text, category_text="QUALCOMM SNAPDRAGON AI CHALLENGE"):
    # Category tag
    tb_cat = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.5), Inches(0.4))
    tf_cat = tb_cat.text_frame
    tf_cat.word_wrap = True
    p_cat = tf_cat.paragraphs[0]
    p_cat.text = category_text.upper()
    p_cat.font.size = Pt(11)
    p_cat.font.bold = True
    p_cat.font.color.rgb = CYAN_ACCENT

    # Main Title
    tb_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.5), Inches(0.8))
    tf_title = tb_title.text_frame
    tf_title.word_wrap = True
    p_title = tf_title.paragraphs[0]
    p_title.text = title_text
    p_title.font.size = Pt(28)
    p_title.font.bold = True
    p_title.font.color.rgb = TEXT_WHITE


def create_pptx():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]

    # -------------------------------------------------------------
    # SLIDE 1: Title Slide
    # -------------------------------------------------------------
    slide1 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide1, BG_COLOR)

    # Accent decorative bar
    bar = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.8), Inches(0.2), Inches(3.6))
    bar.fill.solid()
    bar.fill.fore_color.rgb = CYAN_ACCENT
    bar.line.fill.background()

    tb = slide1.shapes.add_textbox(Inches(1.2), Inches(1.6), Inches(11.0), Inches(4.0))
    tf = tb.text_frame
    tf.word_wrap = True

    p0 = tf.paragraphs[0]
    p0.text = "QUALCOMM SNAPDRAGON AI LAB BUILD & PRESENT CHALLENGE"
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = CYAN_ACCENT

    p1 = tf.add_paragraph()
    p1.text = "SENTINEL"
    p1.font.size = Pt(56)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_WHITE

    p2 = tf.add_paragraph()
    p2.text = "Privacy-First Local Multimodal AI Companion"
    p2.font.size = Pt(24)
    p2.font.bold = True
    p2.font.color.rgb = RGBColor(56, 189, 248)

    p3 = tf.add_paragraph()
    p3.text = "\nSEE  ·  READ  ·  HEAR  ·  REMEMBER  ·  UNDERSTAND  ·  FIND"
    p3.font.size = Pt(14)
    p3.font.bold = True
    p3.font.color.rgb = TEXT_MUTED

    p4 = tf.add_paragraph()
    p4.text = "Local-First Architecture  |  Zero Cloud AI APIs  |  Qualcomm Snapdragon Target"
    p4.font.size = Pt(12)
    p4.font.color.rgb = RGBColor(100, 116, 139)

    # -------------------------------------------------------------
    # SLIDE 2: The Problem
    # -------------------------------------------------------------
    slide2 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide2, BG_COLOR)
    add_header(slide2, "The Fragmentation & Cloud Privacy Dilemma")

    problems = [
        ("Modality Fragmentation", "Vision tools lack memory; chat models cannot see desk hardware; voice transcription lacks spatial awareness; note repositories remain static."),
        ("Cloud Privacy Risk", "Sending live desk camera feeds, confidential documents, or audio to third-party cloud APIs can create significant data privacy and compliance risks."),
        ("Network Latency & Connectivity", "Cloud-dependent workflows introduce network latency and require connectivity, limiting real-time spatial search and preventing offline use."),
        ("Spatial Hallucination", "Cloud models without grounded visual context frequently fabricate object positions, invent document citations, and guess physical coordinates.")
    ]

    for idx, (title, desc) in enumerate(problems):
        col = idx % 2
        row = idx // 2
        left = Inches(0.8 + col * 5.9)
        top = Inches(1.8 + row * 2.5)

        card = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, Inches(5.6), Inches(2.2))
        card.fill.solid()
        card.fill.fore_color.rgb = CARD_BG
        card.line.color.rgb = RGBColor(30, 41, 59)

        tb_c = slide2.shapes.add_textbox(left + Inches(0.3), top + Inches(0.2), Inches(5.0), Inches(1.8))
        tf_c = tb_c.text_frame
        tf_c.word_wrap = True
        p_ct = tf_c.paragraphs[0]
        p_ct.text = title
        p_ct.font.size = Pt(18)
        p_ct.font.bold = True
        p_ct.font.color.rgb = CYAN_ACCENT

        p_cd = tf_c.add_paragraph()
        p_cd.text = desc
        p_cd.font.size = Pt(13)
        p_cd.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------
    # SLIDE 3: The Solution
    # -------------------------------------------------------------
    slide3 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide3, BG_COLOR)
    add_header(slide3, "The Solution: Unified On-Device Physical Intelligence")

    # Left Column: Principles
    tb_sol = slide3.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(5.5), Inches(5.0))
    tf_sol = tb_sol.text_frame
    tf_sol.word_wrap = True

    points = [
        ("Local-First Architecture", "Core perception, speech, memory, and retrieval run on-device with no external network calls for verified components."),
        ("No Cloud AI Dependencies", "No calls to OpenAI, Anthropic, or remote inference servers. All embeddings, OCR, detection, and speech run locally."),
        ("Real Visual Grounding", "Rather than abstract text, SENTINEL highlights physical objects directly on camera via structured HIGHLIGHT_OBJECT actions."),
        ("Epistemic Fact-Checking", "Strictly separates confirmed observations from retrieved evidence and speculative inferences; rejects hallucinated locations.")
    ]

    for t, d in points:
        p_t = tf_sol.add_paragraph() if tf_sol.paragraphs[0].text else tf_sol.paragraphs[0]
        p_t.text = f"• {t}"
        p_t.font.size = Pt(16)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_WHITE
        p_d = tf_sol.add_paragraph()
        p_d.text = f"   {d}\n"
        p_d.font.size = Pt(12)
        p_d.font.color.rgb = TEXT_MUTED

    # Right Column: System Flow Diagram Box
    card_flow = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8))
    card_flow.fill.solid()
    card_flow.fill.fore_color.rgb = CARD_BG
    card_flow.line.color.rgb = CYAN_ACCENT

    tb_flow = slide3.shapes.add_textbox(Inches(7.1), Inches(2.1), Inches(5.1), Inches(4.2))
    tf_flow = tb_flow.text_frame
    tf_flow.word_wrap = True
    pf_title = tf_flow.paragraphs[0]
    pf_title.text = "THE UNIFIED INTERACTION LOOP"
    pf_title.font.size = Pt(14)
    pf_title.font.bold = True
    pf_title.font.color.rgb = CYAN_ACCENT

    steps = [
        ("1. SENSORS (Live)", "Camera (YOLO-X) + Microphone (Whisper-Tiny)"),
        ("2. EXTRACTION (OCR)", "EasyOCR text extracted & bound to desk objects"),
        ("3. RETRIEVAL (Vector)", "Hybrid MiniLM cosine similarity + lexical search"),
        ("4. ORCHESTRATOR", "Evidence collection & token budget management"),
        ("5. REASONING", "Target VLM synthesis with citation verification"),
        ("6. GROUNDED ACTION", "Animated cyan highlight pulse on target object")
    ]
    for s_t, s_d in steps:
        p_s = tf_flow.add_paragraph()
        p_s.text = f"{s_t} : {s_d}"
        p_s.font.size = Pt(11)
        p_s.font.color.rgb = TEXT_WHITE

    # -------------------------------------------------------------
    # SLIDE 4: Architecture
    # -------------------------------------------------------------
    slide4 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide4, BG_COLOR)
    add_header(slide4, "System Architecture: Decoupled & Snapdragon-Ready")

    arch_layers = [
        ("PRESENTATION LAYER", "Next.js 16 + React 19 + TailwindCSS | Dark Glassmorphic Cockpit | Zero Cloud Calls"),
        ("ORCHESTRATION LAYER", "SentinelOrchestrator: Modality Normalization, Evidence Collection, Context Budgeting, Action Dispatch"),
        ("AI SERVICE LAYER", "VisionEngine (YOLO-X) | OCREngine (CRAFT/CRNN) | SpeechEngine (Whisper) | MemoryRetriever (MiniLM)"),
        ("RUNTIME ADAPTER LAYER", "Abstract Execution Boundaries: CPURuntimeAdapter (Host) <-> QNNRuntimeAdapter (Qualcomm Hexagon NPU)"),
        ("STORAGE & DATA LAYER", "Local SQLite Database + Ephemeral RAM Buffers (Zero Raw Media Persisted)")
    ]

    for idx, (layer, details) in enumerate(arch_layers):
        top = Inches(1.8 + idx * 1.0)
        card = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), top, Inches(11.7), Inches(0.85))
        card.fill.solid()
        card.fill.fore_color.rgb = CARD_BG
        card.line.color.rgb = RGBColor(30, 41, 59)

        tb_a = slide4.shapes.add_textbox(Inches(1.1), top + Inches(0.1), Inches(11.1), Inches(0.65))
        tf_a = tb_a.text_frame
        tf_a.word_wrap = True
        p_at = tf_a.paragraphs[0]
        p_at.text = layer
        p_at.font.size = Pt(13)
        p_at.font.bold = True
        p_at.font.color.rgb = CYAN_ACCENT

        p_ad = tf_a.add_paragraph()
        p_ad.text = details
        p_ad.font.size = Pt(11)
        p_ad.font.color.rgb = TEXT_WHITE

    # -------------------------------------------------------------
    # SLIDE 5: Core Demo — "Find It" & Visual Grounding
    # -------------------------------------------------------------
    slide5 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide5, BG_COLOR)
    add_header(slide5, "Core Demo: 'Where is my water bottle?'")

    demo_steps = [
        ("Step 1: Spoken Query", "User speaks naturally: 'Where is my water bottle?' Microphone captures audio only on button press."),
        ("Step 2: Local STT (792 ms)", "Whisper-Tiny transcribes speech entirely on host CPU (RTF 0.264x) without cloud APIs."),
        ("Step 3: Intent Classification", "Voice Action Router extracts intent INTENT_FIND_IT and identifies target 'water bottle'."),
        ("Step 4: Spatial Tracking", "Find It matches target against active desk tracks: Track ID track_001 in region 'center_right'."),
        ("Step 5: Visual Grounding", "Returns HIGHLIGHT_OBJECT action. Animated cyan target pulse illuminates the bottle on camera."),
        ("Step 6: Grounded Response", "Assistant responds with observed facts and zone position without hallucinating.")
    ]

    for idx, (title, desc) in enumerate(demo_steps):
        col = idx % 3
        row = idx // 3
        left = Inches(0.8 + col * 3.9)
        top = Inches(1.8 + row * 2.5)

        card = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, Inches(3.7), Inches(2.2))
        card.fill.solid()
        card.fill.fore_color.rgb = CARD_BG
        card.line.color.rgb = RGBColor(6, 182, 212) if idx == 4 else RGBColor(30, 41, 59)

        tb_d = slide5.shapes.add_textbox(left + Inches(0.2), top + Inches(0.2), Inches(3.3), Inches(1.8))
        tf_d = tb_d.text_frame
        tf_d.word_wrap = True
        p_dt = tf_d.paragraphs[0]
        p_dt.text = title
        p_dt.font.size = Pt(15)
        p_dt.font.bold = True
        p_dt.font.color.rgb = CYAN_ACCENT

        p_dd = tf_d.add_paragraph()
        p_dd.text = desc
        p_dd.font.size = Pt(11)
        p_dd.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------
    # SLIDE 6: Multimodal Intelligence & Epistemic Tiers
    # -------------------------------------------------------------
    slide6 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide6, BG_COLOR)
    add_header(slide6, "Epistemic Fact-Checking: Beyond Mere Text Generation")

    tiers = [
        ("OBSERVED FACTS (Camera & OCR)", "Directly verified via active vision detections and OCR text regions. Example: 'I can see a microcontroller board in center and a notebook with text Embedded System Notes.'", GREEN_ACCENT),
        ("RETRIEVED FACTS (Memory & Docs)", "Verified citations from SQLite memory records or ingested PDF chunks. Example: 'Your saved note #101 specifies operating voltage is 3.3V with timer prescalers set to 1MHz.'", CYAN_ACCENT),
        ("INFERRED HYPOTHESES (Reasoning)", "Logical deductions explicitly marked as inference rather than direct observation. Example: 'The board appears configured for peripheral sensor testing.'", AMBER_ACCENT),
        ("UNCERTAINTIES (Grounded Limits)", "When evidence is absent, the system acknowledges missing data rather than fabricating facts. Example: 'I cannot determine what is inside the closed enclosure.'", RGBColor(239, 68, 68))
    ]

    for idx, (title, desc, color) in enumerate(tiers):
        top = Inches(1.8 + idx * 1.3)
        card = slide6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), top, Inches(11.7), Inches(1.15))
        card.fill.solid()
        card.fill.fore_color.rgb = CARD_BG
        card.line.color.rgb = color

        tb_t = slide6.shapes.add_textbox(Inches(1.1), top + Inches(0.1), Inches(11.1), Inches(0.95))
        tf_t = tb_t.text_frame
        tf_t.word_wrap = True
        p_tt = tf_t.paragraphs[0]
        p_tt.text = title
        p_tt.font.size = Pt(14)
        p_tt.font.bold = True
        p_tt.font.color.rgb = color

        p_td = tf_t.add_paragraph()
        p_td.text = desc
        p_td.font.size = Pt(11)
        p_td.font.color.rgb = TEXT_WHITE

    # -------------------------------------------------------------
    # SLIDE 7: Privacy by Design
    # -------------------------------------------------------------
    slide7 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide7, BG_COLOR)
    add_header(slide7, "Privacy by Design: Zero Ambient Surveillance")

    priv_items = [
        ("Microphone IDLE by Default", "Audio capture requires explicit user push-to-talk. Hardware stream is immediately stopped (MediaStreamTrack.stop()) upon release."),
        ("Camera User Control", "Desk tracking runs only while user keeps camera active. Navigating away releases device handles and clears tracking cache."),
        ("Zero Raw Media Disk Persistence", "Video frames and audio streams are processed exclusively in volatile RAM. No raw media is saved to disk or SQLite."),
        ("Zero Cloud AI Core Dependencies", "No external calls to OpenAI, Anthropic, Google, or remote servers. All embeddings, OCR, and detection run locally."),
        ("Strict User-Curated Memory", "Observations and chat history never auto-contaminate persistent knowledge cards without user confirmation."),
        ("Anti-Surveillance Guarantees", "Categorically rejects facial recognition, biometric identity scanning, and passive ambient room monitoring.")
    ]

    for idx, (title, desc) in enumerate(priv_items):
        col = idx % 2
        row = idx // 2
        left = Inches(0.8 + col * 5.9)
        top = Inches(1.8 + row * 1.7)

        card = slide7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, Inches(5.6), Inches(1.5))
        card.fill.solid()
        card.fill.fore_color.rgb = CARD_BG
        card.line.color.rgb = RGBColor(16, 185, 129)

        tb_p = slide7.shapes.add_textbox(left + Inches(0.3), top + Inches(0.15), Inches(5.0), Inches(1.2))
        tf_p = tb_p.text_frame
        tf_p.word_wrap = True
        p_pt = tf_p.paragraphs[0]
        p_pt.text = title
        p_pt.font.size = Pt(14)
        p_pt.font.bold = True
        p_pt.font.color.rgb = GREEN_ACCENT

        p_pd = tf_p.add_paragraph()
        p_pd.text = desc
        p_pd.font.size = Pt(11)
        p_pd.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------
    # SLIDE 8: Qualcomm Snapdragon Deployment
    # -------------------------------------------------------------
    slide8 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide8, BG_COLOR)
    add_header(slide8, "Snapdragon Deployment & Hardware Separation")

    # Host Card
    card_host = slide8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0))
    card_host.fill.solid()
    card_host.fill.fore_color.rgb = CARD_BG
    card_host.line.color.rgb = RGBColor(100, 116, 139)

    tb_h = slide8.shapes.add_textbox(Inches(1.1), Inches(2.0), Inches(5.0), Inches(4.5))
    tf_h = tb_h.text_frame
    tf_h.word_wrap = True
    p_ht = tf_h.paragraphs[0]
    p_ht.text = "CURRENT DEVELOPMENT HOST"
    p_ht.font.size = Pt(16)
    p_ht.font.bold = True
    p_ht.font.color.rgb = RGBColor(148, 163, 184)

    h_points = [
        "Hardware: Intel Core i5-12450H (x86_64, Windows 11)",
        "Active Provider: CPUExecutionProvider / PyTorch FP32",
        "Vision Status: VERIFIED on Host CPU (88.3 ms)",
        "OCR Status: VERIFIED on Host CPU (380 ms)",
        "Voice Status: VERIFIED on Host CPU (792.9 ms, RTF 0.264x)",
        "Semantic Memory: VERIFIED on Host CPU (16.4 ms)",
        "Truthful Disclosure: NPU execution is NOT VERIFIED on Intel machine."
    ]
    for hp in h_points:
        p = tf_h.add_paragraph()
        p.text = f"• {hp}"
        p.font.size = Pt(11)
        p.font.color.rgb = TEXT_WHITE

    # Snapdragon Target Card
    card_snap = slide8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0))
    card_snap.fill.solid()
    card_snap.fill.fore_color.rgb = CARD_BG
    card_snap.line.color.rgb = CYAN_ACCENT

    tb_s = slide8.shapes.add_textbox(Inches(7.1), Inches(2.0), Inches(5.1), Inches(4.5))
    tf_s = tb_s.text_frame
    tf_s.word_wrap = True
    p_st = tf_s.paragraphs[0]
    p_st.text = "SNAPDRAGON PRODUCTION TARGET"
    p_st.font.size = Pt(16)
    p_st.font.bold = True
    p_st.font.color.rgb = CYAN_ACCENT

    s_points = [
        "Platform: Snapdragon X Elite / X Plus Copilot+ PCs",
        "OS Target: Windows 11 ARM64",
        "Target Accelerator: 45 TOPS Qualcomm Hexagon NPU",
        "Runtime Stack: Qualcomm AI Engine Direct (QNN) & GenieX",
        "YOLO-X: Target INT8 (w8a8) Hexagon acceleration (~3.2 ms ref)",
        "Whisper: Target QNN INT8 Hexagon acceleration (<0.08 RTF)",
        "VLM: Qwen3-VL-4B-Instruct target via Qualcomm GenieX",
        "Status: Target Architecture Configured; NPU verification pending physical Copilot+ PC validation."
    ]
    for sp in s_points:
        p = tf_s.add_paragraph()
        p.text = f"• {sp}"
        p.font.size = Pt(11)
        p.font.color.rgb = TEXT_WHITE

    # -------------------------------------------------------------
    # SLIDE 9: Empirical Validation & Measurements
    # -------------------------------------------------------------
    slide9 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide9, BG_COLOR)
    add_header(slide9, "Empirical Validation & Benchmark Results")

    metrics = [
        ("145 / 145", "Backend Tests Passing", "Zero failed tests across vision, OCR, memory, tracking, speech, and orchestrator."),
        ("RTF 0.2643", "Speech-to-Text RTF", "Whisper-Tiny transcribes 3.0s audio in 792.9 ms (>3.7x faster than real time on CPU)."),
        ("88.34 ms", "YOLO-X Object Detection", "Aspect-ratio preserving letterbox + decoupled NMS scoring on host CPU."),
        ("7.89 ms", "Query Embedding Latency", "MiniLM 384-d semantic encoding with batch throughput of 273.1 items/sec."),
        ("26.2 ms", "Orchestration Overhead", "Dynamic evidence aggregation, priority budgeting, and action derivation outside VLM."),
        ("0 Errors", "TypeScript & ESLint", "Clean Next.js static production bundle compiled with 10 static routes.")
    ]

    for idx, (stat, label, detail) in enumerate(metrics):
        col = idx % 3
        row = idx // 3
        left = Inches(0.8 + col * 3.9)
        top = Inches(1.8 + row * 2.5)

        card = slide9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, Inches(3.7), Inches(2.2))
        card.fill.solid()
        card.fill.fore_color.rgb = CARD_BG
        card.line.color.rgb = RGBColor(30, 41, 59)

        tb_m = slide9.shapes.add_textbox(left + Inches(0.2), top + Inches(0.15), Inches(3.3), Inches(1.9))
        tf_m = tb_m.text_frame
        tf_m.word_wrap = True
        p_ms = tf_m.paragraphs[0]
        p_ms.text = stat
        p_ms.font.size = Pt(28)
        p_ms.font.bold = True
        p_ms.font.color.rgb = CYAN_ACCENT

        p_ml = tf_m.add_paragraph()
        p_ml.text = label
        p_ml.font.size = Pt(13)
        p_ml.font.bold = True
        p_ml.font.color.rgb = TEXT_WHITE

        p_md = tf_m.add_paragraph()
        p_md.text = detail
        p_md.font.size = Pt(10)
        p_md.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------
    # SLIDE 10: Submission Roadmap & Summary
    # -------------------------------------------------------------
    slide10 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide10, BG_COLOR)
    add_header(slide10, "Submission Readiness & What Makes SENTINEL Win")

    card_fin = slide10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(11.7), Inches(4.8))
    card_fin.fill.solid()
    card_fin.fill.fore_color.rgb = CARD_BG
    card_fin.line.color.rgb = CYAN_ACCENT

    tb_fin = slide10.shapes.add_textbox(Inches(1.2), Inches(2.1), Inches(10.9), Inches(4.2))
    tf_fin = tb_fin.text_frame
    tf_fin.word_wrap = True

    p_ft = tf_fin.paragraphs[0]
    p_ft.text = "COMPETITION SUBMISSION READY"
    p_ft.font.size = Pt(18)
    p_ft.font.bold = True
    p_ft.font.color.rgb = CYAN_ACCENT

    f_points = [
        ("Clean, Reproducible Codebase", "Zero committed model binaries, zero secrets, complete .env.example, and verified automated verify_installation.py."),
        ("Complete Deliverables Package", "Brief Project Description (PDF), Short Pitch Deck (PPTX & PDF), 12-Step Canonical Demo Script, and Third-Party License Notices."),
        ("Strict Technical Honesty", "Host Intel CPU results are clearly documented; Snapdragon Hexagon NPU is accurately reported as NOT VERIFIED until hardware validation."),
        ("True Grounded Innovation", "Combines computer vision, spatial desk tracking, voice recognition, and semantic memory into a private assistant that actually interacts with the physical world.")
    ]
    for ft, fd in f_points:
        p_h = tf_fin.add_paragraph()
        p_h.text = f"✔ {ft}"
        p_h.font.size = Pt(14)
        p_h.font.bold = True
        p_h.font.color.rgb = TEXT_WHITE
        p_d = tf_fin.add_paragraph()
        p_d.text = f"    {fd}"
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = TEXT_MUTED

    prs.save(str(PPTX_PATH))
    print(f"[OK] Pitch PPTX successfully written to: {PPTX_PATH}")


def create_pdf_from_pptx():
    """Generates the companion pitch deck PDF using ReportLab with matching dark styling."""
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'PitchTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#F8FAFC')
    )
    subtitle_style = ParagraphStyle(
        'PitchSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#06B6D4')
    )
    body_style = ParagraphStyle(
        'PitchBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#94A3B8')
    )
    card_title_style = ParagraphStyle(
        'CardTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#06B6D4')
    )
    card_body_style = ParagraphStyle(
        'CardBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#F8FAFC')
    )

    story = []

    slides_content = [
        {
            "cat": "QUALCOMM SNAPDRAGON AI LAB BUILD & PRESENT CHALLENGE",
            "title": "SENTINEL — Privacy-First Local Multimodal AI Companion",
            "body": "A privacy-first local multimodal AI companion that sees, reads, hears, remembers, understands, and helps users find information across their workspace.<br/><br/><b>SEE  ·  READ  ·  HEAR  ·  REMEMBER  ·  UNDERSTAND  ·  FIND</b><br/><br/>100% On-Device Execution  |  Zero Cloud APIs  |  Qualcomm Snapdragon Copilot+ PC Target Architecture",
            "boxes": [
                ("Local Perception", "Continuous desk object tracking via YOLO-X and EasyOCR text extraction."),
                ("Local Speech & Memory", "Local Whisper STT (<800ms) with dense vector semantic search in SQLite."),
                ("Epistemic Fact-Checking", "ResponseValidator separates confirmed observations from inferences."),
                ("Target Platform", "Designed for Qualcomm Snapdragon X-series Windows Copilot+ PCs.")
            ]
        },
        {
            "cat": "PROBLEM STATEMENT",
            "title": "The Fragmentation & Cloud Privacy Dilemma",
            "body": "Existing AI assistants fail in physical desktop environments due to architectural siloing and cloud dependency:",
            "boxes": [
                ("Modality Fragmentation", "Vision tools don't remember context; chat models cannot see desk hardware; voice transcription lacks spatial coordinates."),
                ("Cloud Privacy Risk", "Sending live desk cameras or confidential prototype schematics to cloud APIs can create enterprise security and compliance risks."),
                ("Network Latency & Connectivity", "Cloud-dependent workflows introduce latency and require connectivity; offline operation is impossible."),
                ("Spatial Hallucination", "Generic cloud LLMs guess object positions and invent document citations without physical grounding.")
            ]
        },
        {
            "cat": "SOLUTION OVERVIEW",
            "title": "The Solution: Unified On-Device Physical Intelligence",
            "body": "SENTINEL integrates computer vision, document intelligence, voice understanding, and spatial memory into one unified local-first multimodal loop. Core components run on-device; Snapdragon QNN runtime path prepared for hardware validation.",
            "boxes": [
                ("SEE & TRACK", "YOLO-X detection with deterministic IoU + centroid tracking, EMA smoothing. Verified on host CPU."),
                ("READ & REMEMBER", "EasyOCR spatial binding + MiniLM 384-d vector embeddings with strict project isolation. Verified on host CPU."),
                ("UNDERSTAND", "Evidence-aware multimodal orchestration with strict token budget management."),
                ("FIND & GROUND", "Find It spatial localization returning structured HIGHLIGHT_OBJECT visual pulses.")
            ]
        },
        {
            "cat": "SYSTEM ARCHITECTURE",
            "title": "Decoupled Architecture & Snapdragon Readiness",
            "body": "The application separates UI presentation from AI model runtimes via decoupled adapter boundaries:",
            "boxes": [
                ("Presentation Layer", "Next.js 16 + React 19 + TailwindCSS cockpit with zero external analytics or network calls."),
                ("Orchestration Layer", "SentinelOrchestrator coordinates input normalization, dynamic evidence collection, and validation."),
                ("AI Service Layer", "VisionEngine, OCREngine, SpeechEngine, and MemoryRetriever operating locally."),
                ("Runtime Adapters", "CPURuntimeAdapter (host development) <-> QNNRuntimeAdapter (Snapdragon Copilot+ PC target).")
            ]
        },
        {
            "cat": "CORE DEMONSTRATION",
            "title": "Canonical Demo: 'Where is my water bottle?'",
            "body": "The primary competition demonstration showcases the complete physical-to-digital loop:",
            "boxes": [
                ("1. Natural Spoken Query", "User asks by voice: 'Where is my water bottle?' Microphone captures only on hold."),
                ("2. Local STT (792 ms)", "Whisper-Tiny transcribes speech entirely on host CPU (RTF 0.264x) without cloud offload."),
                ("3. Intent & Spatial Match", "VoiceRouter delegates to FindItService, resolving target track_001 in 'center_right'."),
                ("4. Interactive Grounding", "Returns HIGHLIGHT_OBJECT action; animated cyan pulse illuminates the bottle on camera.")
            ]
        },
        {
            "cat": "REASONING & SAFETY",
            "title": "Epistemic Fact-Checking: Beyond Text Generation",
            "body": "SENTINEL enforces strict epistemic separation to eliminate hallucination in physical environments:",
            "boxes": [
                ("Observed Facts", "Directly verified via active vision detections and OCR text regions on the desk."),
                ("Retrieved Facts", "Verified source citations from SQLite memory notes or ingested PDF document chunks."),
                ("Inferred Hypotheses", "Logical conclusions explicitly marked as deduction rather than direct camera observation."),
                ("Grounded Uncertainties", "Explicitly reports unknown when evidence is absent rather than guessing.")
            ]
        },
        {
            "cat": "PRIVACY & SECURITY",
            "title": "Privacy by Design: Zero Ambient Surveillance",
            "body": "Strict architectural privacy guarantees enforce complete user sovereignty over physical data:",
            "boxes": [
                ("Microphone Default OFF", "Capture is strictly click-to-record; hardware handles release immediately upon release."),
                ("Camera Lifecycle Control", "Camera tracking executes only while explicitly active; leaving page purges state."),
                ("Zero Media Persistence", "Video frames and audio streams are processed in RAM; zero raw media saved to disk."),
                ("Anti-Surveillance", "Categorically rejects facial recognition, biometric profiling, and ambient room monitoring.")
            ]
        },
        {
            "cat": "QUALCOMM SNAPDRAGON",
            "title": "Snapdragon Deployment & Hardware Separation",
            "body": "Architectural separation preserves strict technical truthfulness between host and target profiles:",
            "boxes": [
                ("Development Host", "12th Gen Intel Core i5-12450H (x86_64, Windows 11) running CPUExecutionProvider."),
                ("NPU Verification Status", "Physical NPU execution is NOT VERIFIED on Intel host; zero fabricated metrics."),
                ("Snapdragon Target", "Targeted for Snapdragon X-series Windows ARM64 PCs with 45 TOPS Hexagon NPU."),
                ("Optimization Stack", "Qualcomm AI Engine Direct (QNN), QAIRT, and Qualcomm GenieX runtime architecture.")
            ]
        },
        {
            "cat": "EMPIRICAL BENCHMARKS",
            "title": "Validation & Measured Host Telemetry",
            "body": "All metrics represent genuine, empirical measurements on the active workstation:",
            "boxes": [
                ("145 / 145 Tests Passed", "Full backend test suite passing in 33.7s; 0 TypeScript errors; 0 lint warnings."),
                ("Whisper RTF = 0.2643", "Real speech benchmark: 792.9 ms inference on 3.0s audio (>3.7x faster than real time)."),
                ("YOLO-X: 88.34 ms", "Real-time object detection with aspect-ratio letterboxing on local CPU."),
                ("MiniLM: 7.89 ms", "384-dimensional query embedding with batch throughput of 273 items/sec.")
            ]
        },
        {
            "cat": "COMPETITION CONCLUSION",
            "title": "Submission Readiness & What Makes SENTINEL Win",
            "body": "SENTINEL delivers a complete, grounded, reproducible submission candidate:",
            "boxes": [
                ("Clean Repository", "Zero committed model binaries, zero secrets, and automated pre-flight verifier."),
                ("Complete Package", "Official Brief Description (PDF), Pitch Deck (PPTX & PDF), and Canonical Demo Script."),
                ("Truthful Benchmarks", "Host CPU results clearly documented; Snapdragon NPU targets cleanly separated."),
                ("Physical Innovation", "True on-device physical AI that bridges desktop reality with digital memory.")
            ]
        }
    ]

    for s_idx, slide_data in enumerate(slides_content):
        story.append(Paragraph(slide_data["cat"], subtitle_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(slide_data["title"], title_style))
        story.append(Spacer(1, 8))
        story.append(Paragraph(slide_data["body"], body_style))
        story.append(Spacer(1, 14))

        # 2x2 Grid of visual cards
        b = slide_data["boxes"]
        table_data = [
            [
                Paragraph(f"<b>{b[0][0]}</b><br/>{b[0][1]}", card_body_style),
                Paragraph(f"<b>{b[1][0]}</b><br/>{b[1][1]}", card_body_style)
            ],
            [
                Paragraph(f"<b>{b[2][0]}</b><br/>{b[2][1]}", card_body_style),
                Paragraph(f"<b>{b[3][0]}</b><br/>{b[3][1]}", card_body_style)
            ]
        ]
        t = Table(table_data, colWidths=[360, 360], rowHeights=[75, 75])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#0F172A')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#1E293B')),
            ('INNERGRID', (0,0), (-1,-1), 8, colors.HexColor('#0B0F19')),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 12),
            ('RIGHTPADDING', (0,0), (-1,-1), 12),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(t)

        if s_idx < len(slides_content) - 1:
            story.append(PageBreak())

    def draw_bg(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor('#0B0F19'))
        canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=True, stroke=False)
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_bg, onLaterPages=draw_bg)
    print(f"[OK] Pitch PDF successfully written to: {PDF_PATH}")


if __name__ == "__main__":
    create_pptx()
    create_pdf_from_pptx()
