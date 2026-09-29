# Qualcomm Snapdragon Hardware & AI Runtime Architecture

This document defines SENTINEL's technical integration with Qualcomm Snapdragon platforms, the Hexagon Neural Processing Unit (NPU), Qualcomm AI Engine Direct (QNN), and ONNX Runtime.

---

## 1. Why Snapdragon Matters for SENTINEL

SENTINEL is built upon the promise: **"Your private AI that sees, understands, and remembers."**

To observe physical desk environments, recognize tools, and track user workflows continuously, SENTINEL cannot rely on cloud APIs (privacy risk, network latency, subscription cost) or heavy host CPU/discrete GPU inference (high thermals, battery drain, fan noise).

The Qualcomm Snapdragon Copilot+ platform (Snapdragon X Elite, Snapdragon X Plus, and Snapdragon X2) provides:
- **Dedicated Hexagon NPU (45 TOPS)**: Purpose-built tensor acceleration for vision, audio, and reasoning graphs.
- **Extreme Energy Efficiency**: Continuous background inference with minimal battery footprint and silent fanless or low-acoustic operation.
- **Guaranteed Edge Privacy**: Sensor data (camera frames, audio) is processed entirely within the local NPU memory boundary.

---

## 2. What the NPU Does

The Neural Processing Unit (NPU) is a specialized hardware accelerator engineered for dense tensor mathematical operations:
- High-throughput INT8 and FP16 matrix multiplications (GEMM)
- Spatial 2D/3D convolutions for computer vision feature extraction
- Transformer attention mechanisms and vector dot products
- Hardware-accelerated activation functions (SiLU, ReLU, GELU)

Unlike CPUs, which handle serial control flow, or discrete GPUs, which consume substantial power for high-bandwidth graphics rendering, the Hexagon NPU optimizes throughput-per-watt for continuous AI inference.

---

## 3. What QNN (Qualcomm AI Engine Direct) Does

**Qualcomm AI Engine Direct (QNN)** is Qualcomm's unified software architecture and SDK for AI acceleration across Snapdragon platforms.

Key functions:
1. **Graph Compilation**: Transforms ONNX or TensorFlow graphs into hardware-optimized QNN context binaries (`.serialized.bin` / HTP format).
2. **Hardware Target Routing**: Dispatches graph nodes to the optimal execution core:
   - `QnnHtp`: Qualcomm Hexagon Tensor Processor (NPU)
   - `QnnGpu`: Qualcomm Adreno GPU
   - `QnnCpu`: Qualcomm Oryon / Kryo CPU
3. **Execution Provider Integration**: QNN implements the ONNX Runtime Execution Provider interface (`QNNExecutionProvider`), allowing standard ONNX models to execute directly on the Hexagon NPU without custom C++ device drivers.

---

## 4. How ONNX Runtime Fits into SENTINEL

SENTINEL adopts **ONNX Runtime (ORT)** as its core inference layer because of its clean Execution Provider (EP) abstraction:

```
SENTINEL Application Layer (FastAPI / VisionService)
                       ↓
         InferenceEngine / VisionModelAdapter
                       ↓
              ONNX Runtime Session
                       ↓
     ┌─────────────────┴─────────────────┐
     ↓                                   ↓
QNNExecutionProvider           CPUExecutionProvider
     ↓                                   ↓
Qualcomm Hexagon NPU            Host Processor Fallback
(Snapdragon Copilot+ Target)   (Development Machine Staging)
```

This architecture ensures SENTINEL remains **portable**:
- On Snapdragon Copilot+ PCs with Qualcomm drivers installed: `QNNExecutionProvider` activates, offloading vision computation to the Hexagon NPU.
- On non-Snapdragon development machines (e.g. x86_64 Intel/AMD workstations): `CPUExecutionProvider` activates automatically, enabling complete end-to-end development, testing, and debugging without breaking application workflows.

---

## 5. Model Selection Framework

SENTINEL does not select models based on subjective marketing claims. Models in the registry are evaluated against six technical gates:

| Technical Gate | Criteria |
|---|---|
| **Target Hardware Compatibility** | Explicit support on Snapdragon X Elite, X Plus, or X2 platforms. |
| **Runtime Compatibility** | Proven export to standard ONNX with validated tensor layouts. |
| **Provider Compatibility** | Support for `QNNExecutionProvider` and CPU fallback. |
| **Input/Output Geometry** | Normalized spatial resolution (e.g. 640x640x3) and clean bounding box format. |
| **Licensing** | Permissive licenses (e.g. Apache 2.0) preferred over restrictive copyleft (AGPL-3.0). |
| **Verification State** | Strict separation of reference vendor benchmarks from locally measured metrics. |

---

## 6. How Verification Occurs

SENTINEL enforces a strict separation between **Hardware Detection** and **Hardware Execution Verification**:

1. **Hardware Detection (`npu_detected: true`)**:
   - The OS reports an NPU device in the Windows Device Tree (e.g., under the Neural Processors class `{9da4941da-78e7-4976-9055-6dd8a6a24683}`).
   - **Crucial Rule**: A detected NPU is *not* proof of AI inference acceleration.
2. **Provider Availability (`qnn_available: true`)**:
   - `QNNExecutionProvider` is registered in `ort.get_available_providers()`.
   - **Crucial Rule**: Provider registration is *not* proof of NPU inference.
3. **Hardware Execution Verification (`npu_execution_verified: true`)**:
   - Set to `true` **only** after an actual vision model session has been initialized with `QNNExecutionProvider`, executed forward inference passes on real image data, and verified node offloading to the Hexagon NPU.
   - In Phase 2A, `npu_execution_verified` remains strictly `false`.

---

## 7. Current Verification Status (Step 2 Vision & Step 3 Semantic Memory)

| Component | Status | Verification Method | Notes |
|---|---|---|---|
| **Host Hardware Discovery** | **VERIFIED** | Live System Diagnostics | Discovered real OS, CPU, RAM, and GPU. |
| **Target Separation** | **VERIFIED** | Target Profile Loader | Distinguishes dev host from Snapdragon target. |
| **ONNX Runtime Engine** | **VERIFIED** | Package & Provider Probe | ONNX Runtime v1.30.0 registered and operational. |
| **CPU Execution Provider** | **VERIFIED** | Session & Inference Execution | Host fallback provider active; runs live YOLO-X & embeddings. |
| **Real Local Vision Model** | **VERIFIED** | Live Model Session & Inference | YOLO-X (Small) ONNX loaded; real detections & bounding boxes. |
| **Local Vision Latency** | **VERIFIED (MEASURED)** | Empirical 15-run controlled benchmark | Mean: 88.34 ms (Total Pipeline: 104.9 ms). |
| **Local OCR Engine** | **VERIFIED** | Live CRAFT+CRNN execution | EasyOCR on Host CPU (~330-450 ms). |
| **Embedding Engine Architecture** | **VERIFIED** | 4-tier decoupled adapter architecture | MemoryService → EmbeddingEngine → ModelAdapter → RuntimeAdapter. |
| **Host Local Embedding Model** | **VERIFIED (MEASURED)** | Live model inference (`all-MiniLM-L6-v2`) | Single: 16.41 ms, Query: 7.89 ms, Batch: 273.1 items/sec. |
| **Snapdragon Target Embedding Model** | **TARGET CONFIGURED** | Qualcomm AI Hub (`nomic-embed-text-v1.5`) | 137M params, 523MB, 768-d, ready for QNN EP on Snapdragon. |
| **Semantic & Hybrid Retrieval** | **VERIFIED** | SQLite BLOB + Cosine Similarity | Pure semantic, pure keyword, and weighted hybrid search. |
| **Document Chunk Retrieval** | **VERIFIED** | Controlled chunk retrieval | Evidence returned with document ID, page, and chunk index. |
| **QNN Execution Provider** | **UNVERIFIED (Target)** | Pending Snapdragon Target | Targeted for Snapdragon Copilot+ hardware deployment. |
| **NPU Inference Execution** | **NOT VERIFIED** | Truthful Telemetry Policy | Strictly reported as NOT VERIFIED on host CPU fallback. |

