# SENTINEL Vision Engine — Host CPU Baseline Report

> **Authoritative Baseline Measurement for Step 2 Vision Stabilization**  
> Generated: `2026-09-29T10:44:30Z`

---

## 1. Executive Summary

This report establishes the measured performance baseline for the **YOLO-X** local vision pipeline running on the development host CPU. 

**Critical Hardware Note**:
- **Current Execution**: `Host CPU (Intel)` via `CPUExecutionProvider`
- **Snapdragon NPU Target**: `NOT_VERIFIED` (Target: `Qualcomm Snapdragon X Elite NPU (Hexagon)`)
- No cross-hardware comparisons, NPU simulations, or synthetic accelerations are asserted.

---

## 2. Host Environment & Model Specification

| Property | Value |
| :--- | :--- |
| **Host Operating System** | `Windows-11-10.0.26200-SP0` |
| **Host Processor** | `Intel64 Family 6 Model 154 Stepping 3, GenuineIntel` |
| **Host Architecture** | `AMD64` |
| **Python Environment** | `v3.13.15` |
| **Model Architecture** | `YOLO-X (Small)` |
| **Model Artifact** | `yolox_s.onnx (34.2 MB)` |
| **Input Resolution** | `640x640 (3-channel float32 RGB)` |
| **Output Classes** | `80 COCO classes` |
| **License** | `Apache-2.0` |

---

## 3. Measured Memory Footprint

| Metric | Measured Value |
| :--- | :--- |
| **Model Artifact on Disk** | `34.2 MB` |
| **Process RSS (Before Load)** | `37.91 MB` |
| **Process RSS (After Session Load)** | `102.46 MB` |
| **Model Process Memory Impact** | `64.55 MB` |
| **Process RSS (After Inference)** | `172.71 MB` |

---

## 4. Latency Distribution & Stage Breakdown

### Cold Start Pass
- **Model Weight Load Latency**: `300.787 ms`
- **First Inference Latency (Cold Graph)**: `92.049 ms`
- **First Total Pipeline Latency**: `132.057 ms`

### Warm Steady-State Inference (15 Measured Passes)
| Metric | Latency |
| :--- | :--- |
| **Raw Inference (Mean)** | **`88.34 ms`** |
| **Raw Inference (Median)** | **`88.36 ms`** |
| **Raw Inference (Min)** | **`81.15 ms`** |
| **Raw Inference (Max)** | **`100.67 ms`** |
| **Raw Inference (Std Dev)** | **`5.1 ms`** |

### Complete End-to-End Pipeline Breakdown (Mean)
| Stage | Mean Duration | Percentage |
| :--- | :--- | :--- |
| **1. Preprocessing** (Aspect-ratio letterbox, normalization) | `12.27 ms` | `11.7%` |
| **2. Inference** (ONNX Runtime CPU forward pass) | `88.34 ms` | `84.2%` |
| **3. Postprocessing** (Anchor unstriding, score filter, NMS) | `4.23 ms` | `4.0%` |
| **Total End-to-End Latency** | **`104.9 ms`** | 100% |

---

## 5. Throughput Telemetry

- **Estimated Theoretical Throughput**: **`11.32 FPS`**
- *Note*: Estimated theoretical throughput based on raw warm inference pass latency (1000ms / mean_inference_ms). Not a live continuous camera stream FPS.

---

## 6. Sample Live Detections

The benchmark verified live detection output on real test scenes:
```json
[
  {
    "label": "laptop",
    "confidence": 0.9614,
    "bbox": {
      "x": 0.24819999933242798,
      "y": 0.01810000091791153,
      "width": 0.4927000105381012,
      "height": 0.9027000069618225,
      "x_min": 0.24819999933242798,
      "y_min": 0.01810000091791153,
      "x_max": 0.7408999800682068,
      "y_max": 0.920799970626831,
      "x_abs_min": 341.49,
      "y_abs_min": 13.91,
      "x_abs_max": 1019.5,
      "y_abs_max": 707.19
    }
  },
  {
    "label": "mouse",
    "confidence": 0.9231,
    "bbox": {
      "x": 0.7491000294685364,
      "y": 0.6735000014305115,
      "width": 0.1137000024318695,
      "height": 0.26010000705718994,
      "x_min": 0.7491000294685364,
      "y_min": 0.6735000014305115,
      "x_max": 0.8626999855041504,
      "y_max": 0.9336000084877014,
      "x_abs_min": 1030.69,
      "y_abs_min": 517.27,
      "x_abs_max": 1187.09,
      "y_abs_max": 717.02
    }
  },
  {
    "label": "cup",
    "confidence": 0.9001,
    "bbox": {
      "x": 0.13770000636577606,
      "y": 0.2371000051498413,
      "width": 0.1460999995470047,
      "height": 0.26350000500679016,
      "x_min": 0.13770000636577606,
      "y_min": 0.2371000051498413,
      "x_max": 0.28380000591278076,
      "y_max": 0.5005000233650208,
      "x_abs_min": 189.5,
      "y_abs_min": 182.08,
      "x_abs_max": 390.46,
      "y_abs_max": 384.41
    }
  },
  {
    "label": "cell phone",
    "confidence": 0.803,
    "bbox": {
      "x": 0.8920999765396118,
      "y": 0.34290000796318054,
      "width": 0.10769999772310257,
      "height": 0.22259999811649323,
      "x_min": 0.8920999765396118,
      "y_min": 0.34290000796318054,
      "x_max": 0.9998000264167786,
      "y_max": 0.5654000043869019,
      "x_abs_min": 1227.5,
      "y_abs_min": 263.32,
      "x_abs_max": 1375.68,
      "y_abs_max": 434.25
    }
  },
  {
    "label": "potted plant",
    "confidence": 0.7388,
    "bbox": {
      "x": 0.871399998664856,
      "y": 0.08630000054836273,
      "width": 0.07829999923706055,
      "height": 0.19370000064373016,
      "x_min": 0.871399998664856,
      "y_min": 0.08630000054836273,
      "x_max": 0.9495999813079834,
      "y_max": 0.2800000011920929,
      "x_abs_min": 1198.98,
      "y_abs_min": 66.28,
      "x_abs_max": 1306.66,
      "y_abs_max": 215.04
    }
  }
]
```
