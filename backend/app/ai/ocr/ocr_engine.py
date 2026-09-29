from __future__ import annotations

import datetime as dt
import logging
import threading
import time
import uuid
from typing import Any
import numpy as np
from PIL import Image

from app.ai.ocr.ocr_adapter import EasyOCRAdapter, OCRModelAdapter
from app.ai.pipeline import ModelLifecycleState
from app.core.benchmark_manager import BenchmarkRecord, benchmark_manager
from app.schemas.ocr import OCRResult, OCRStatusResponse

logger = logging.getLogger("sentinel.ai.ocr.engine")


class OCREngine:
    """
    Thread-safe lifecycle manager for the local OCR pipeline.
    Maintains model sessions, manages state transitions, and records stage latencies.
    """

    def __init__(self, adapter: OCRModelAdapter | None = None) -> None:
        self._lock = threading.RLock()
        self._adapter: OCRModelAdapter = adapter or EasyOCRAdapter()
        self._state: ModelLifecycleState = (
            ModelLifecycleState.AVAILABLE if self._adapter.is_available() else ModelLifecycleState.UNAVAILABLE
        )
        self._error_message: str | None = None
        self._warm_runs: int = 0
        self._first_inference_ms: float | None = None

    @property
    def state(self) -> ModelLifecycleState:
        return self._state

    def is_available(self) -> bool:
        return self._adapter.is_available()

    def is_ready(self) -> bool:
        return self._state == ModelLifecycleState.READY and self._adapter.is_loaded()

    def ensure_loaded(self, languages: list[str] | None = None) -> None:
        with self._lock:
            if self._state == ModelLifecycleState.READY and self._adapter.is_loaded():
                return

            if not self._adapter.is_available():
                self._state = ModelLifecycleState.UNAVAILABLE
                raise RuntimeError("OCR model dependencies are not installed or available.")

            self._state = ModelLifecycleState.LOADING
            try:
                load_start = time.perf_counter()
                self._adapter.load(languages=languages)
                load_ms = round((time.perf_counter() - load_start) * 1000.0, 2)
                self._state = ModelLifecycleState.READY
                self._error_message = None
                logger.info("OCR Engine initialized and ready in %s ms.", load_ms)
            except Exception as e:
                self._state = ModelLifecycleState.ERROR
                self._error_message = str(e)
                logger.exception("Failed to load OCR Engine: %s", e)
                raise RuntimeError(f"OCR Engine failed to initialize: {e}") from e

    def unload(self) -> None:
        with self._lock:
            self._adapter.unload()
            self._state = (
                ModelLifecycleState.AVAILABLE if self._adapter.is_available() else ModelLifecycleState.UNAVAILABLE
            )
            self._warm_runs = 0
            logger.info("OCR Engine unloaded from memory.")

    def process_image(
        self,
        image_data: Image.Image | np.ndarray | bytes,
        confidence_threshold: float = 0.2,
    ) -> OCRResult:
        with self._lock:
            self.ensure_loaded()
            self._state = ModelLifecycleState.RUNNING
            try:
                raw_res = self._adapter.process_image(
                    image_data=image_data,
                    confidence_threshold=confidence_threshold,
                )
                self._warm_runs += 1
                if self._first_inference_ms is None and raw_res.get("timing"):
                    self._first_inference_ms = raw_res["timing"].total_ms

                self._state = ModelLifecycleState.READY

                return OCRResult(
                    status="READY",
                    message=f"OCR pass complete: {raw_res['region_count']} text regions recognized.",
                    regions=raw_res["regions"],
                    full_text=raw_res["full_text"],
                    region_count=raw_res["region_count"],
                    timing=raw_res["timing"],
                    model=self._adapter.get_metadata(),
                    execution_provider=raw_res.get("active_provider", "CPUExecutionProvider"),
                    device="Host CPU (CPUExecutionProvider)",
                    npu_verified=raw_res.get("npu_verified", False),
                    source="image",
                )
            except Exception as e:
                self._state = ModelLifecycleState.READY
                logger.exception("OCR inference execution failed: %s", e)
                raise

    def get_status(self) -> OCRStatusResponse:
        meta = self._adapter.get_metadata()
        active_provider = getattr(self._adapter, "get_active_provider", lambda: "CPUExecutionProvider")()
        npu_verified = getattr(self._adapter, "is_npu_verified", lambda: False)()
        return OCRStatusResponse(
            state=self._state.value,
            is_available=self._adapter.is_available(),
            is_loaded=self._adapter.is_loaded(),
            model_name=meta.name,
            detector=meta.detector,
            recognizer=meta.recognizer,
            runtime=meta.runtime,
            execution_provider=active_provider,
            npu_verified=npu_verified,
            supported_languages=meta.languages,
            device_label="Host CPU (Development Fallback)" if not npu_verified else "Snapdragon NPU",
        )

    def run_benchmark(
        self,
        sample_img: Image.Image | bytes,
        warmup_runs: int = 2,
        measured_runs: int = 5,
    ) -> BenchmarkRecord:
        """Runs formal benchmark passes for detector and recognizer stages."""
        self.ensure_loaded()

        for _ in range(warmup_runs):
            self.process_image(sample_img)

        det_times: list[float] = []
        rec_times: list[float] = []
        total_times: list[float] = []

        for _ in range(measured_runs):
            res = self.process_image(sample_img)
            if res.timing:
                det_times.append(res.timing.detector_ms)
                rec_times.append(res.timing.recognizer_ms)
                total_times.append(res.timing.total_ms)

        mean_total = round(float(np.mean(total_times)), 2)
        mean_det = round(float(np.mean(det_times)), 2)
        mean_rec = round(float(np.mean(rec_times)), 2)
        median_total = round(float(np.median(total_times)), 2)
        min_total = round(float(np.min(total_times)), 2)
        max_total = round(float(np.max(total_times)), 2)
        std_dev = round(float(np.std(total_times)), 2)
        throughput = round(1000.0 / mean_total, 2) if mean_total > 0 else 0.0

        now = dt.datetime.now(dt.timezone.utc)
        record = BenchmarkRecord(
            id=str(uuid.uuid4())[:8],
            model_name="EasyOCR (CRAFT + CRNN)",
            model_version="1.7.2",
            runtime="Local PyTorch (CPU Fallback)",
            execution_provider="CPUExecutionProvider",
            device="Host CPU (CPUExecutionProvider)",
            timestamp=now,
            input_type="Text Sample Image",
            load_time_ms=None,
            first_inference_ms=self._first_inference_ms,
            average_inference_ms=mean_total,
            throughput=throughput,
            memory_mb=None,
            notes=(
                f"OCR Benchmark: {measured_runs} runs. Mean: {mean_total}ms (Detector: {mean_det}ms, Recognizer: {mean_rec}ms). "
                f"Median: {median_total}ms, Min: {min_total}ms, Max: {max_total}ms, StdDev: {std_dev}ms. "
                f"NPU Acceleration: NOT VERIFIED (Host CPU)."
            ),
        )

        benchmark_manager.record_run(record)
        return record


# Global singleton OCR engine
ocr_engine = OCREngine()
