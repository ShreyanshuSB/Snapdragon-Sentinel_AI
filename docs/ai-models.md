# SENTINEL AI Model Registry & Candidate Evaluation

This document outlines SENTINEL's model selection framework, candidate models evaluated from Qualcomm AI Hub, and the roadmap toward multimodal reasoning.

---

## 1. Vision Model Status (Step 8 — Real Local Vision Verified)

All candidate models are evaluated using official Qualcomm AI Hub metadata and Windows object detection reference implementations.

| Model Candidate | Official Source | License | Format | Input Shape | Quantization | QNN Support | AI Hub Ref Latency (ms)* | SENTINEL Measured Latency |
|---|---|---|---|---|---|---|---|---|
| **YOLO-X (Small)** | [Qualcomm AI Hub Windows Sample](https://aihub.qualcomm.com/apps/object_detection_windows_cpp) | **Apache-2.0** | ONNX | 1x3x640x640 | FP32 / w8a8 (INT8) | Verified | 3.2 ms (312 fps) [Snapdragon X Elite Ref] | **88.34 ms (11.32 fps) [Host CPU Measured]** |
| **YOLOv8-Det** | [Qualcomm AI Hub Model Catalog](https://aihub.qualcomm.com/compute/models/yolov8_det) | AGPL-3.0 | ONNX | 1x3x640x640 | w8a8 (INT8) / FP16 | Supported | 3.8 ms (263 fps) | *Not measured* |
| **YOLOv10-Det**| [Qualcomm AI Hub Model Catalog](https://aihub.qualcomm.com/compute/models/yolov10_det) | AGPL-3.0 | ONNX | 1x3x640x640 | w8a8 (INT8) / FP16 | Supported | 3.5 ms (285 fps) | *Not measured* |
| **YOLOv11-Det**| [Qualcomm AI Hub Model Catalog](https://aihub.qualcomm.com/compute/models/yolo_v11_det) | AGPL-3.0 | ONNX | 1x3x640x640 | w8a8 (INT8) / FP16 | Supported | 3.4 ms (294 fps) | *Not measured* |

*\*Note: AI Hub Reference Latency reflects Qualcomm AI Hub benchmarks on Snapdragon X Elite reference hardware. SENTINEL Measured Latency reflects empirical measurements on this machine.*

---

## 2. Integrated Model: YOLO-X (Small)

**YOLO-X** is fully integrated as SENTINEL's first operational AI model:

1. **Model Artifact**:
   - Location: `models/vision/yolox_s.onnx`
   - Model Size: 34.2 MB (9.0M parameters)
   - Source: Official Megvii / Qualcomm AI Hub reference export
   - License: Apache-2.0 (Permissive, non-viral)
   - Input Tensor: `images` `[1, 3, 640, 640]` `float32`
   - Output Tensor: `output` `[1, 8400, 85]` `float32`

2. **Preprocessing Pipeline**:
   - Aspect-ratio preserving resize: `scale = min(640 / H, 640 / W)`
   - Color space: RGB to BGR (OpenCV/Megvii convention)
   - Padding: Constant value 114 (YOLO-X gray padding) to 640x640
   - Tensor layout: Transposed to `[1, 3, 640, 640]` contiguous float32

3. **Postprocessing & Coordinate Decoding**:
   - Multi-stride anchor unstriding across strides `[8, 16, 32]` (8400 total grid anchors)
   - Decoupled scoring: `confidence = objectness * class_probability`
   - Confidence threshold filtering (default: 0.25)
   - Class-aware Non-Maximum Suppression (NMS) with IoU threshold 0.45
   - Exact reverse coordinate mapping: normalized `[0, 1]` coordinates and original pixel coordinates

4. **Hardware Verification on Current Machine**:
   - Host Processor: Intel CPU (x86_64 Development Staging)
   - Active Provider: `CPUExecutionProvider`
   - NPU Verification State: `NOT VERIFIED` (`LOCAL • CPU`)
   - Measured Steady-State Latency: Mean 88.34 ms, Median 88.36 ms, Min 81.15 ms, Max 100.67 ms, StdDev 5.10 ms (Total Pipeline Mean: 104.9 ms)

---

## 3. Integrated OCR Model: EasyOCR (CRAFT + CRNN)

**EasyOCR** is integrated as SENTINEL's local document intelligence and workspace text extraction engine:

1. **Components**:
   - **Text Detector**: CRAFT (*Character Region Awareness for Text Detection*) — 20.8M parameters
   - **Text Recognizer**: CRNN (*Convolutional Recurrent Neural Network with CTC loss*) — 3.8M parameters
   - **Source**: Qualcomm AI Hub Target Architecture / PyTorch Engine
   - **License**: Apache-2.0

2. **Pipeline Performance (Measured on Host)**:
   - CRAFT Detector Latency: ~250 ms
   - CRNN Recognizer Latency: ~80 ms
   - Total OCR Latency: ~330 - 450 ms per image
   - Execution Provider: `CPUExecutionProvider` (Local Host CPU Fallback)
   - NPU Verification State: `NOT VERIFIED` (`LOCAL • CPU`)

3. **Qualcomm AI Hub Target Compatibility**:
   - Qualcomm AI Hub lists EasyOCR detector and recognizer components running through QNN on Snapdragon X Elite and X2 Elite reference platforms.
   - For this staging machine, execution cleanly falls back to local CPU without faking NPU execution.

---

## 4. Text Embedding Models (Step 3 — Local Semantic Memory Verified)

### Candidate Target: Nomic-Embed-Text v1.5
- **Official Source**: [Qualcomm AI Hub Model Catalog - nomic_embed_text_v1_5](https://aihub.qualcomm.com/compute/models/nomic_embed_text_v1_5)
- **Parameters**: 137M
- **Model Artifact Size**: ~523 MB (Float)
- **License**: Apache-2.0
- **Supported Platforms**: Snapdragon X Elite, Snapdragon X Plus 8-Core, Snapdragon X2 Elite
- **Qualcomm AI Hub Status**: Verified NPU jobs available via QNN
- **Adapter**: `NomicEmbedTextAdapter` (architecture complete, requires `einops` for direct PyTorch CPU evaluation)
- **Target Provider**: `QNNExecutionProvider` (Qualcomm Hexagon NPU)
- **Target Dimensions**: 768

### Active Host Baseline: all-MiniLM-L6-v2
- **Official Source**: SentenceTransformers / Hugging Face local artifact
- **Parameters**: 22.7M
- **Model Artifact Size**: 87 MB
- **License**: Apache-2.0
- **Input Modality**: Text (max sequence length 256 / 512 tokens)
- **Embedding Dimension**: 384-d
- **Adapter**: `SentenceTransformerEmbeddingAdapter`
- **Execution Provider**: `CPUExecutionProvider` (Local Host CPU Fallback)
- **Current Device**: Intel CPU Development Machine
- **NPU Verification State**: `NOT VERIFIED` (`LOCAL • CPU`)
- **Measured Host CPU Latencies**:
  - Model Cold Load Time: `5,277 ms`
  - Single Text Embedding: `16.41 ms` (mean of 5)
  - Query Embedding: `7.89 ms` (mean of 5)
  - Batch Embedding (5 items): `18.31 ms` (throughput: **273.1 items/sec**)
  - Vector Similarity Search: `2.24 ms`

---

## 5. Reference Metrics vs. SENTINEL Measured Metrics

To maintain absolute technical truthfulness:
- **Reference Metrics**: Stored under `reference_metrics` with clear attribution to `Qualcomm AI Hub Reference Device (Snapdragon X Elite)`.
- **SENTINEL Measured Metrics**: Stored under `our_metrics`. These fields remain `null` / `"Not measured"` until genuine end-to-end inference has been performed on the active machine.

---

## 6. Multimodal Reasoning Model: Qwen3-VL-4B-Instruct (Step 4)

For advanced physical workspace reasoning, scene interpretation, and grounded tool query answering, SENTINEL implements the **ReasoningEngine** and **ReasoningModelAdapter** architecture:
- **Candidate ID**: `qwen3-vl-4b-instruct`
- **Qualcomm AI Hub Status**: Candidate for Snapdragon X Elite, Snapdragon X Plus 8-Core, and Snapdragon X2 Elite.
- **Parameters**: 4 Billion
- **Context Length**: Up to 4,096 tokens
- **Modalities**: Image + Text → Text
- **Target Runtime Stack**: Qualcomm GenieX + QAIRT (Qualcomm AI Engine Direct) targeting Qualcomm Hexagon NPU
- **Host Staging Status**: `NOT_AVAILABLE_ON_HOST` (Host machine is Intel CPU with < 2 GB available RAM; VLM inference requires ARM64 Copilot+ PC or dedicated hardware).
- **Host NPU Status**: `NOT VERIFIED` (truthfully reported across UI and API).
- **Reasoning Architecture**: 4-tier decoupled pipeline (`ConversationService` → `ReasoningEngine` → `ReasoningModelAdapter` → `RuntimeAdapter` → Model). Full retrieval, context budgeting, prompt injection defense, and source attribution verified.

---

## 7. Real-Time Workspace Tracking & Spatial Model (Step 5)

For continuous physical desk understanding and "Find It" spatial search, SENTINEL implements:
- **Object Tracker**: Deterministic multi-stage 2D tracker operating over YOLO-X detections with IoU and centroid distance matching.
- **Temporal Smoothing**: Exponential Moving Average (EMA) smoothing ($\alpha = 0.65$) on normalized coordinates to eliminate visual jitter.
- **Spatial Reasoning**: 9 normalized workspace zones and pairwise geometric relationships (`left_of`, `right_of`, `above`, `below`, `near`, `overlaps`).
- **Observation Memory (TTL)**: 4 discrete observation states (`CURRENT_VISIBLE`, `RECENTLY_SEEN`, `STALE`, `EXPIRED`) keeping spatial observations separate from permanent user memories.
- **Find It Engine**: Hierarchical natural-language resolver combining user aliases, OCR text, and canonical class synonyms with explicit uncertainty states (`NOT_FOUND`, `AMBIGUOUS`).

---

## 8. Speech-to-Text Models (Step 6 — Local Voice Engine Verified)

For local-first voice interaction and spoken workspace queries, SENTINEL implements the **SpeechEngine** and **SpeechModelAdapter** architecture:

### Active Host Baseline: OpenAI Whisper-Tiny
- **Candidate ID**: `whisper-tiny`
- **Official Source**: Hugging Face / Transformers (`openai/whisper-tiny`)
- **Parameters**: ~39M
- **Model Artifact Size**: ~151 MB (FP32)
- **License**: Apache-2.0 (Permissive, commercial and distribution friendly)
- **Input Format**: 16,000 Hz single-channel mono PCM float32
- **Supported Languages**: Multilingual (English primary, auto-language detection)
- **Execution Provider**: PyTorch CPU / Local Execution Provider (`CPUExecutionProvider`)
- **Current Host Device**: Intel CPU Development Machine
- **Host Availability Status**: `AVAILABLE` / `VERIFIED`
- **Measured Inference Latency**: `1,417.2 ms` (on 3.0s audio buffer)
- **Measured Real-Time Factor (RTF)**: `0.472` (> 2x faster than real-time on host CPU)

### Qualcomm Snapdragon Target: Whisper-Base Snapdragon
- **Candidate ID**: `whisper-base-snapdragon`
- **Official Source**: Qualcomm AI Hub Model Catalog (`whisper_base_en`)
- **Parameters**: ~74M
- **Model Format**: ONNX INT8 Quantized (w8a8)
- **Target Runtime Stack**: Qualcomm AI Engine Direct (QAIRT) / QNN Execution Provider
- **Target Accelerator**: Qualcomm Hexagon NPU (Snapdragon X Elite / Copilot+ PC)
- **Qualcomm AI Hub Status**: Verified QNN INT8 execution available on reference hardware
- **Host Hardware Status**: `NOT_AVAILABLE_ON_HOST` (Hexagon NPU runtime requires Windows ARM64)
- **Host Verification State**: `NOT_VERIFIED` (truthfully reported; no simulated acceleration)
- **Expected Snapdragon Reference RTF**: `< 0.08` (> 12x faster than real-time on Hexagon NPU)

---

## 9. Comprehensive Model Provenance & License Audit (Step 7 Verified)

| Model Name / Candidate | Exact Artifact Identifier / Repository | Source Repository | Artifact License | Upstream Code License | Runtime Stack | Target Hardware | Current Verification State |
|---|---|---|---|---|---|---|---|
| **YOLO-X (Small)** | `yolox_s.onnx` / `yolox_tiny.onnx` | [Megvii-BaseDetection/YOLOX](https://github.com/Megvii-BaseDetection/YOLOX) | **Apache-2.0** | Apache-2.0 | ONNX Runtime (`CPUExecutionProvider`) | Qualcomm Hexagon NPU (Snapdragon X Elite) | **VERIFIED (Host CPU)** • Target NPU: `NOT VERIFIED` |
| **EasyOCR (CRAFT + CRNN)** | `craft_mlt_25k.pth`, `english_g2.pth` | [JaidedAI/EasyOCR](https://github.com/JaidedAI/EasyOCR) | **Apache-2.0** | Apache-2.0 | PyTorch Dynamic Quant (`CPUExecutionProvider`) | Qualcomm Hexagon NPU via QNN | **VERIFIED (Host CPU)** • Target NPU: `NOT VERIFIED` |
| **all-MiniLM-L6-v2** | `sentence-transformers/all-MiniLM-L6-v2` | [Hugging Face sentence-transformers](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) | **Apache-2.0** | Apache-2.0 | Hugging Face Transformers / PyTorch | Host CPU / Staging | **VERIFIED (Host CPU)** |
| **Nomic-Embed-Text v1.5** | `nomic-ai/nomic-embed-text-v1.5` | [Qualcomm AI Hub Model Catalog](https://aihub.qualcomm.com/compute/models/nomic_embed_text_v1_5) | **Apache-2.0** | Apache-2.0 | Qualcomm QNN / GenieX | Qualcomm Hexagon NPU (Snapdragon X Elite) | Target Configured • Host: `NOT_AVAILABLE_ON_HOST` |
| **Whisper-Tiny** | `openai/whisper-tiny` | [Hugging Face openai/whisper-tiny](https://huggingface.co/openai/whisper-tiny) | **Apache-2.0** *(Hugging Face Artifact)* | **MIT** *(OpenAI Upstream Repo)* | Hugging Face Transformers / PyTorch FP32 | Qualcomm Hexagon NPU / Host CPU | **VERIFIED (Host CPU, RTF 0.264)** • Target NPU: `NOT VERIFIED` |
| **Qwen3-VL-4B-Instruct** | `qwen3-vl-4b-instruct` | [Qualcomm AI Hub Compute](https://aihub.qualcomm.com/compute) | **Apache-2.0** | Apache-2.0 | Qualcomm GenieX + QAIRT (Windows ARM64) | Qualcomm Hexagon NPU (Snapdragon Copilot+ PC) | Target Configured • Host: `NOT_AVAILABLE_ON_HOST` |

*Note: For OpenAI Whisper, the upstream software repository is released under MIT, while the Hugging Face model repository and distributed model card are governed under Apache-2.0. Both licenses are permissive, non-viral, and suitable for distribution.*

---

## 10. Model Ingestion & Safety Policy

1. **Zero Silent Downloads**: SENTINEL will never silently download large model weights in the background.
2. **Local Storage Only**: Model weights are stored in `models/` or local cache and excluded from git version control.
3. **Hardware Acceleration Gate**: Before claiming hardware acceleration, SENTINEL's pipeline requires explicit validation via the execution provider state machine (`RUNNING` → `VERIFIED`).
4. **Offline Operation Guarantee**: Following initial download, all core model inference routines execute completely offline with zero network connectivity.
