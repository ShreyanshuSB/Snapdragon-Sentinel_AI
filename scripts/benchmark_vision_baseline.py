"""
Controlled Host CPU Benchmark & Baseline Measurement for YOLO-X Vision Pipeline.
Measures:
1. Model file size on disk
2. Process memory (RSS) before and after model load
3. Cold start model load latency
4. Cold start first inference latency (including graph compilation)
5. Warmup inference runs (3 passes)
6. Measured steady-state inference runs (15 passes)
7. Separate metrics for preprocess, inference, postprocess, and total latency
8. Statistical distribution: mean, median, min, max, std dev
9. Estimated theoretical single-stream throughput
10. Generates structured JSON and Markdown baseline reports
"""

from __future__ import annotations

import gc
import json
import logging
import os
import platform
import sys
import time
from pathlib import Path
import numpy as np
from PIL import Image
from typing import Any

sys.path.insert(0, "backend")

from app.ai.vision.inference_engine import YOLOXInferenceEngine
from app.core.benchmark_manager import benchmark_manager
from app.schemas.benchmark import BenchmarkRecord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vision_benchmark")


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (np.floating, np.integer)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def get_process_memory_mb() -> float | None:
    """Measures process RSS in MB using ctypes on Windows or psutil if available."""
    try:
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        GetProcessMemoryInfo = ctypes.windll.psapi.GetProcessMemoryInfo
        GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
        GetProcessMemoryInfo.restype = wintypes.BOOL

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return round(counters.WorkingSetSize / (1024 * 1024), 2)
    except Exception:
        pass

    try:
        import psutil
        process = psutil.Process(os.getpid())
        return round(process.memory_info().rss / (1024 * 1024), 2)
    except Exception:
        return None


def run_controlled_vision_benchmark() -> dict:
    test_image_path = Path("backend/tests/test_assets/workspace_16_9.jpg")
    if not test_image_path.exists():
        raise FileNotFoundError(f"Test asset missing: {test_image_path}")

    pil_img = Image.open(test_image_path)
    orig_w, orig_h = pil_img.size

    # Force garbage collection before measurement
    gc.collect()
    mem_before_mb = get_process_memory_mb()

    # Instantiate fresh engine to measure cold load
    engine = YOLOXInferenceEngine()
    model_file_size_mb = round(os.path.getsize(engine.model_path) / (1024 * 1024), 2)

    # 1. Cold start model load
    t0 = time.perf_counter()
    engine.ensure_loaded()
    load_time_ms = round((time.perf_counter() - t0) * 1000.0, 3)

    mem_after_load_mb = get_process_memory_mb()
    load_mem_delta_mb = round(mem_after_load_mb - mem_before_mb, 2)

    active_provider = engine.runtime_adapter.get_active_provider()
    is_npu = engine.runtime_adapter.is_npu_verified()

    # 2. Cold start first inference
    t_cold = time.perf_counter()
    cold_res = engine.detect_objects(pil_img, confidence_threshold=0.25)
    cold_total_ms = round((time.perf_counter() - t_cold) * 1000.0, 3)
    cold_inf_ms = cold_res["timing"]["inference_ms"]

    # 3. Warmup passes (3 passes)
    warmup_passes = 3
    for _ in range(warmup_passes):
        engine.detect_objects(pil_img, confidence_threshold=0.25)

    # 4. Measured passes (15 passes)
    measured_runs = 15
    preprocess_times: list[float] = []
    inference_times: list[float] = []
    postprocess_times: list[float] = []
    total_times: list[float] = []

    for _ in range(measured_runs):
        res = engine.detect_objects(pil_img, confidence_threshold=0.25)
        preprocess_times.append(res["timing"]["preprocess_ms"])
        inference_times.append(res["timing"]["inference_ms"])
        postprocess_times.append(res["timing"]["postprocess_ms"])
        total_times.append(res["timing"]["total_ms"])

    mem_after_inference_mb = get_process_memory_mb()

    # Compute statistics
    inf_mean = round(float(np.mean(inference_times)), 2)
    inf_median = round(float(np.median(inference_times)), 2)
    inf_min = round(float(np.min(inference_times)), 2)
    inf_max = round(float(np.max(inference_times)), 2)
    inf_std = round(float(np.std(inference_times)), 2)

    pre_mean = round(float(np.mean(preprocess_times)), 2)
    post_mean = round(float(np.mean(postprocess_times)), 2)
    total_mean = round(float(np.mean(total_times)), 2)
    total_median = round(float(np.median(total_times)), 2)

    theoretical_throughput_fps = round(1000.0 / inf_mean, 2) if inf_mean > 0 else 0.0

    report = {
        "metadata": {
            "title": "SENTINEL Vision Engine Host CPU Baseline Benchmark",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "environment": {
                "host_os": platform.platform(),
                "processor": platform.processor(),
                "architecture": platform.machine(),
                "python_version": platform.python_version(),
            },
            "hardware_classification": {
                "current_device": "Host CPU (Intel)",
                "active_execution_provider": active_provider,
                "npu_acceleration_status": "NOT_VERIFIED",
                "target_platform": "Qualcomm Snapdragon X Elite NPU (Hexagon)",
                "note": "This measurement represents the Host CPU development baseline. It does NOT represent Snapdragon NPU performance.",
            },
        },
        "model": {
            "name": "YOLO-X",
            "variant": engine.model_variant,
            "filename": engine.model_path.name,
            "file_size_mb": model_file_size_mb,
            "input_resolution": f"{engine.model_width}x{engine.model_height}",
            "classes": 80,
            "license": "Apache-2.0",
        },
        "memory": {
            "process_rss_before_load_mb": mem_before_mb,
            "process_rss_after_load_mb": mem_after_load_mb,
            "model_memory_impact_mb": load_mem_delta_mb,
            "process_rss_after_inference_mb": mem_after_inference_mb,
        },
        "latencies_ms": {
            "cold_start_load_ms": load_time_ms,
            "cold_start_first_inference_ms": cold_inf_ms,
            "cold_start_total_pipeline_ms": cold_total_ms,
            "warm_runs_count": measured_runs,
            "raw_inference": {
                "mean_ms": inf_mean,
                "median_ms": inf_median,
                "min_ms": inf_min,
                "max_ms": inf_max,
                "std_dev_ms": inf_std,
            },
            "stages_mean": {
                "preprocess_ms": pre_mean,
                "inference_ms": inf_mean,
                "postprocess_ms": post_mean,
                "total_pipeline_ms": total_mean,
                "total_pipeline_median_ms": total_median,
            },
        },
        "throughput": {
            "theoretical_single_stream_fps": theoretical_throughput_fps,
            "note": "Estimated theoretical throughput based on raw warm inference pass latency (1000ms / mean_inference_ms). Not a live continuous camera stream FPS.",
        },
        "sample_detections": [
            {
                "label": d["label"],
                "confidence": d["confidence"],
                "bbox": d["bbox"],
            }
            for d in cold_res["detections"][:5]
        ],
    }

    # Save to BenchmarkManager
    import datetime as dt
    import uuid

    record = BenchmarkRecord(
        id=str(uuid.uuid4())[:8],
        model_name=f"YOLO-X ({engine.model_variant})",
        model_version="1.0",
        runtime="ONNX Runtime v1.30.0",
        execution_provider=active_provider,
        device=f"Host CPU ({active_provider})",
        timestamp=dt.datetime.now(dt.timezone.utc),
        input_type=f"{engine.model_width}x{engine.model_height} RGB Image",
        load_time_ms=load_time_ms,
        first_inference_ms=cold_inf_ms,
        average_inference_ms=inf_mean,
        throughput=theoretical_throughput_fps,
        memory_mb=load_mem_delta_mb,
        notes=(
            f"Step 2 Host CPU Baseline ({measured_runs} measured runs): "
            f"Inf Mean={inf_mean}ms, Median={inf_median}ms, Min={inf_min}ms, Max={inf_max}ms, StdDev={inf_std}ms. "
            f"Preprocess={pre_mean}ms, Postprocess={post_mean}ms, Total={total_mean}ms. "
            f"Snapdragon NPU: NOT VERIFIED."
        ),
    )
    benchmark_manager.record_run(record)

    # Update dashboard summary metrics
    b = benchmark_manager._benchmarks
    b["model_load_time"]["value"] = load_time_ms
    b["model_load_time"]["status"] = "Measured"
    b["first_inference"]["value"] = cold_inf_ms
    b["first_inference"]["status"] = "Measured"
    b["average_inference"]["value"] = inf_mean
    b["average_inference"]["status"] = "Measured"
    b["throughput"]["value"] = theoretical_throughput_fps
    b["throughput"]["status"] = "Estimated (Theoretical)"
    b["memory_usage"]["value"] = load_mem_delta_mb
    b["memory_usage"]["status"] = "Measured"

    # Save reports
    docs_dir = Path("docs")
    docs_dir.mkdir(parents=True, exist_ok=True)

    def _json_default(obj: Any) -> Any:
        if isinstance(obj, (np.floating, np.integer)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return str(obj)

    json_path = docs_dir / "vision_baseline_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=_json_default)
    logger.info("Saved JSON baseline report to: %s", json_path)

    md_path = docs_dir / "vision_baseline_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(generate_markdown_report(report))
    logger.info("Saved Markdown baseline report to: %s", md_path)

    return report


def generate_markdown_report(r: dict) -> str:
    m = r["metadata"]
    mod = r["model"]
    mem = r["memory"]
    lat = r["latencies_ms"]
    tp = r["throughput"]

    return f"""# SENTINEL Vision Engine — Host CPU Baseline Report

> **Authoritative Baseline Measurement for Step 2 Vision Stabilization**  
> Generated: `{m['timestamp']}`

---

## 1. Executive Summary

This report establishes the measured performance baseline for the **YOLO-X** local vision pipeline running on the development host CPU. 

**Critical Hardware Note**:
- **Current Execution**: `{m['hardware_classification']['current_device']}` via `{m['hardware_classification']['active_execution_provider']}`
- **Snapdragon NPU Target**: `{m['hardware_classification']['npu_acceleration_status']}` (Target: `{m['hardware_classification']['target_platform']}`)
- No cross-hardware comparisons, NPU simulations, or synthetic accelerations are asserted.

---

## 2. Host Environment & Model Specification

| Property | Value |
| :--- | :--- |
| **Host Operating System** | `{m['environment']['host_os']}` |
| **Host Processor** | `{m['environment']['processor']}` |
| **Host Architecture** | `{m['environment']['architecture']}` |
| **Python Environment** | `v{m['environment']['python_version']}` |
| **Model Architecture** | `{mod['name']} ({mod['variant']})` |
| **Model Artifact** | `{mod['filename']} ({mod['file_size_mb']} MB)` |
| **Input Resolution** | `{mod['input_resolution']} (3-channel float32 RGB)` |
| **Output Classes** | `{mod['classes']} COCO classes` |
| **License** | `{mod['license']}` |

---

## 3. Measured Memory Footprint

| Metric | Measured Value |
| :--- | :--- |
| **Model Artifact on Disk** | `{mod['file_size_mb']} MB` |
| **Process RSS (Before Load)** | `{mem['process_rss_before_load_mb']} MB` |
| **Process RSS (After Session Load)** | `{mem['process_rss_after_load_mb']} MB` |
| **Model Process Memory Impact** | `{mem['model_memory_impact_mb']} MB` |
| **Process RSS (After Inference)** | `{mem['process_rss_after_inference_mb']} MB` |

---

## 4. Latency Distribution & Stage Breakdown

### Cold Start Pass
- **Model Weight Load Latency**: `{lat['cold_start_load_ms']} ms`
- **First Inference Latency (Cold Graph)**: `{lat['cold_start_first_inference_ms']} ms`
- **First Total Pipeline Latency**: `{lat['cold_start_total_pipeline_ms']} ms`

### Warm Steady-State Inference ({lat['warm_runs_count']} Measured Passes)
| Metric | Latency |
| :--- | :--- |
| **Raw Inference (Mean)** | **`{lat['raw_inference']['mean_ms']} ms`** |
| **Raw Inference (Median)** | **`{lat['raw_inference']['median_ms']} ms`** |
| **Raw Inference (Min)** | **`{lat['raw_inference']['min_ms']} ms`** |
| **Raw Inference (Max)** | **`{lat['raw_inference']['max_ms']} ms`** |
| **Raw Inference (Std Dev)** | **`{lat['raw_inference']['std_dev_ms']} ms`** |

### Complete End-to-End Pipeline Breakdown (Mean)
| Stage | Mean Duration | Percentage |
| :--- | :--- | :--- |
| **1. Preprocessing** (Aspect-ratio letterbox, normalization) | `{lat['stages_mean']['preprocess_ms']} ms` | `{round(lat['stages_mean']['preprocess_ms'] / lat['stages_mean']['total_pipeline_ms'] * 100, 1)}%` |
| **2. Inference** (ONNX Runtime CPU forward pass) | `{lat['stages_mean']['inference_ms']} ms` | `{round(lat['stages_mean']['inference_ms'] / lat['stages_mean']['total_pipeline_ms'] * 100, 1)}%` |
| **3. Postprocessing** (Anchor unstriding, score filter, NMS) | `{lat['stages_mean']['postprocess_ms']} ms` | `{round(lat['stages_mean']['postprocess_ms'] / lat['stages_mean']['total_pipeline_ms'] * 100, 1)}%` |
| **Total End-to-End Latency** | **`{lat['stages_mean']['total_pipeline_ms']} ms`** | 100% |

---

## 5. Throughput Telemetry

- **Estimated Theoretical Throughput**: **`{tp['theoretical_single_stream_fps']} FPS`**
- *Note*: {tp['note']}

---

## 6. Sample Live Detections

The benchmark verified live detection output on real test scenes:
```json
{json.dumps(r['sample_detections'], indent=2, default=_json_default)}
```
"""


if __name__ == "__main__":
    report = run_controlled_vision_benchmark()
    print("\n=== BENCHMARK COMPLETE ===")
    print(f"Model: {report['model']['name']} ({report['model']['variant']})")
    print(f"Inference Mean: {report['latencies_ms']['raw_inference']['mean_ms']} ms")
    print(f"Inference Median: {report['latencies_ms']['raw_inference']['median_ms']} ms")
    print(f"Inference Min-Max: {report['latencies_ms']['raw_inference']['min_ms']} - {report['latencies_ms']['raw_inference']['max_ms']} ms")
    print(f"Pipeline Total Mean: {report['latencies_ms']['stages_mean']['total_pipeline_ms']} ms")
    print(f"Theoretical Throughput: {report['throughput']['theoretical_single_stream_fps']} FPS")
    print(f"Model Memory Delta: {report['memory']['model_memory_impact_mb']} MB")
