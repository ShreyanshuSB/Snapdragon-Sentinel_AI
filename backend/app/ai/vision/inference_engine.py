from __future__ import annotations

import datetime as dt
import logging
import os
import threading
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any
import numpy as np
from PIL import Image

from app.ai.pipeline import InferenceEngine
from app.ai.vision.onnx_runtime_adapter import ONNXRuntimeAdapter
from app.ai.vision.yolox_adapter import YOLOXAdapter
from app.core.benchmark_manager import benchmark_manager
from app.schemas.benchmark import BenchmarkRecord
from app.schemas.vision import (
    Detection,
    ImageMetadata,
    ModelInferenceMetadata,
    RuntimeVerificationMetadata,
    TimingMetrics,
    VisionResult,
)

logger = logging.getLogger("sentinel.inference_engine")


from app.ai.pipeline import ModelLifecycleState


class YOLOXInferenceEngine(InferenceEngine):
    """
    Production-grade InferenceEngine coordinating YOLO-X vision model adapter
    and ONNX Runtime execution provider adapter.
    Thread-safe, loads once, and accurately tracks cold-start vs warm runs.
    """

    def __init__(self, model_filename: str = "yolox_s.onnx") -> None:
        self._lock = threading.Lock()
        self._state = ModelLifecycleState.UNAVAILABLE
        self._error_message: str | None = None
        self._warm_run_count: int = 0
        self._first_inference_ms: float | None = None

        # Resolve model path
        root_dir = Path(__file__).resolve().parents[4]
        candidate_s = root_dir / "models" / "vision" / "yolox_s.onnx"
        candidate_nano = root_dir / "models" / "vision" / "yolox_nano.onnx"

        if candidate_s.exists():
            self.model_path = candidate_s
            self.model_width = 640
            self.model_height = 640
            self.model_variant = "Small"
        elif candidate_nano.exists():
            self.model_path = candidate_nano
            self.model_width = 416
            self.model_height = 416
            self.model_variant = "Nano"
        else:
            self.model_path = candidate_s
            self.model_width = 640
            self.model_height = 640
            self.model_variant = "Small"

        if self.model_path.exists():
            self._state = ModelLifecycleState.AVAILABLE

        self.model_adapter = YOLOXAdapter(model_width=self.model_width, model_height=self.model_height)
        self.runtime_adapter = ONNXRuntimeAdapter()

    @property
    def state(self) -> ModelLifecycleState:
        return self._state

    def is_ready(self) -> bool:
        return self._state == ModelLifecycleState.READY and self.runtime_adapter.is_loaded()

    def is_available(self) -> bool:
        return self.model_path.exists()

    def ensure_loaded(self) -> None:
        """Loads model weights once into memory in a thread-safe manner."""
        with self._lock:
            if self._state == ModelLifecycleState.READY and self.runtime_adapter.is_loaded():
                return

            if not self.model_path.exists():
                self._state = ModelLifecycleState.UNAVAILABLE
                raise FileNotFoundError(
                    f"YOLO-X model weights not found at: {self.model_path.resolve()}. "
                    f"Please verify model acquisition in models/vision/README.md."
                )

            self._state = ModelLifecycleState.LOADING
            try:
                load_start = time.perf_counter()
                self.runtime_adapter.initialize(str(self.model_path))
                load_time_ms = round((time.perf_counter() - load_start) * 1000.0, 2)
                self._state = ModelLifecycleState.READY
                self._error_message = None
                logger.info(
                    "YOLO-X model (%s) loaded into memory in %s ms. Active provider: %s",
                    self.model_variant,
                    load_time_ms,
                    self.runtime_adapter.get_active_provider(),
                )
            except Exception as e:
                self._state = ModelLifecycleState.ERROR
                self._error_message = str(e)
                logger.exception("Failed to initialize vision model session: %s", e)
                raise RuntimeError(
                    f"Vision model could not be loaded: {str(e)}. "
                    f"Check the model installation and runtime configuration."
                ) from e

    def unload(self) -> None:
        """Safely unloads model from memory."""
        with self._lock:
            self.runtime_adapter.close()
            if self.model_path.exists():
                self._state = ModelLifecycleState.AVAILABLE
            else:
                self._state = ModelLifecycleState.UNAVAILABLE
            self._warm_run_count = 0
            logger.info("Vision model unloaded from memory.")

    def detect_objects(
        self,
        image_data: Image.Image | bytes,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
    ) -> dict[str, Any]:
        """
        Executes complete local vision detection pipeline:
        Image -> Preprocessing -> Local Inference -> Postprocessing / NMS -> Bounding Boxes.
        """
        self.ensure_loaded()

        with self._lock:
            self._state = ModelLifecycleState.RUNNING
            total_start = time.perf_counter()
            try:
                # 1. Preprocess
                pre_start = time.perf_counter()
                inputs, metadata = self.model_adapter.preprocess(image_data)
                preprocess_ms = round((time.perf_counter() - pre_start) * 1000.0, 3)

                # 2. Raw Inference
                inf_outputs = self.runtime_adapter.run_inference(inputs)
                raw_inf_time = inf_outputs.get("_inference_time_ms")
                inference_ms = float(raw_inf_time[0]) if raw_inf_time is not None else 0.0

                # 3. Postprocess
                post_start = time.perf_counter()
                detections = self.model_adapter.postprocess(
                    inf_outputs,
                    metadata=metadata,
                    confidence_threshold=confidence_threshold,
                    iou_threshold=iou_threshold,
                )
                postprocess_ms = round((time.perf_counter() - post_start) * 1000.0, 3)

                total_ms = round((time.perf_counter() - total_start) * 1000.0, 3)

                self._warm_run_count += 1
                if self._first_inference_ms is None:
                    self._first_inference_ms = total_ms

                self._state = ModelLifecycleState.READY

                return {
                    "detections": detections,
                    "metadata": metadata,
                    "timing": {
                        "preprocess_ms": preprocess_ms,
                        "inference_ms": inference_ms,
                        "postprocess_ms": postprocess_ms,
                        "total_ms": total_ms,
                    },
                    "active_provider": self.runtime_adapter.get_active_provider(),
                    "is_npu_verified": self.runtime_adapter.is_npu_verified(),
                }
            except Exception as e:
                self._state = ModelLifecycleState.READY
                logger.exception("Inference execution failed: %s", e)
                raise

    def get_pipeline_status(self) -> dict[str, Any]:
        file_size_mb = (
            round(os.path.getsize(self.model_path) / (1024 * 1024), 2)
            if self.model_path.exists()
            else None
        )
        return {
            "state": self._state.value,
            "model_name": f"YOLO-X ({self.model_variant})",
            "model_path": str(self.model_path),
            "model_size_mb": file_size_mb,
            "input_resolution": f"{self.model_width}x{self.model_height}",
            "active_provider": self.runtime_adapter.get_active_provider(),
            "npu_verified": self.runtime_adapter.is_npu_verified(),
            "warm_runs": self._warm_run_count,
            "first_inference_ms": self._first_inference_ms,
            "error_message": self._error_message,
        }

    def run_benchmark(
        self,
        image_data: Image.Image | bytes,
        warmup_runs: int = 3,
        measured_runs: int = 10,
    ) -> BenchmarkRecord:
        """
        Executes a formal on-device benchmark:
        - Runs warmup_runs (cold start graph warmup)
        - Runs measured_runs (steady-state warm inference)
        - Computes mean, median, min, max, standard deviation
        - Saves to BenchmarkManager without overwriting historical runs.
        """
        self.ensure_loaded()

        # Warmup passes
        for _ in range(warmup_runs):
            self.detect_objects(image_data)

        # Measured steady-state passes
        latencies_ms: list[float] = []
        inf_latencies_ms: list[float] = []
        pre_latencies_ms: list[float] = []
        post_latencies_ms: list[float] = []

        for _ in range(measured_runs):
            res = self.detect_objects(image_data)
            latencies_ms.append(res["timing"]["total_ms"])
            inf_latencies_ms.append(res["timing"]["inference_ms"])
            pre_latencies_ms.append(res["timing"]["preprocess_ms"])
            post_latencies_ms.append(res["timing"]["postprocess_ms"])

        mean_latency = round(float(np.mean(inf_latencies_ms)), 2)
        median_latency = round(float(np.median(inf_latencies_ms)), 2)
        min_latency = round(float(np.min(inf_latencies_ms)), 2)
        max_latency = round(float(np.max(inf_latencies_ms)), 2)
        std_dev = round(float(np.std(inf_latencies_ms)), 2)

        mean_pre = round(float(np.mean(pre_latencies_ms)), 2)
        mean_post = round(float(np.mean(post_latencies_ms)), 2)
        mean_total = round(float(np.mean(latencies_ms)), 2)
        throughput_fps = round(1000.0 / mean_latency, 2) if mean_latency > 0 else 0.0

        now = dt.datetime.now(dt.timezone.utc)
        record = BenchmarkRecord(
            id=str(uuid.uuid4())[:8],
            model_name=f"YOLO-X ({self.model_variant})",
            model_version="1.0",
            runtime="ONNX Runtime v1.30.0",
            execution_provider=self.runtime_adapter.get_active_provider(),
            device=f"Host CPU ({self.runtime_adapter.get_active_provider()})",
            timestamp=now,
            input_type=f"{self.model_width}x{self.model_height} RGB Image",
            load_time_ms=None,
            first_inference_ms=self._first_inference_ms,
            average_inference_ms=mean_latency,
            preprocess_ms=mean_pre,
            postprocess_ms=mean_post,
            total_pipeline_ms=mean_total,
            cold_warm="warm",
            throughput=throughput_fps,
            memory_mb=None,
            notes=(
                f"Steady-state benchmark: {measured_runs} runs. "
                f"Mean: {mean_latency}ms, Median: {median_latency}ms, "
                f"Min: {min_latency}ms, Max: {max_latency}ms, StdDev: {std_dev}ms. "
                f"Preprocess: {mean_pre}ms, Postprocess: {mean_post}ms, Total: {mean_total}ms. "
                f"NPU Acceleration: NOT VERIFIED (CPU Fallback active)."
            ),
        )

        benchmark_manager.record_run(record)
        return record


# Global singleton inference engine
inference_engine = YOLOXInferenceEngine()
