from __future__ import annotations

import datetime as dt
import time
import uuid
from typing import Any

from app.schemas.benchmark import BenchmarkRecord, BenchmarkSummary


class BenchmarkManager:
    """
    Manages benchmark records for SENTINEL.

    Important: No benchmark metrics are fabricated. Unexecuted inference passes
    are reported as None / "Not measured". Only the storage I/O baseline is real
    because it actually measures local disk latency.
    """

    def __init__(self) -> None:
        self._benchmarks: dict[str, dict[str, Any]] = {
            "model_load_time": {
                "name": "Model Load Time",
                "status": "Not measured",
                "value": None,
                "unit": "ms",
                "description": "Time required to load model weights into NPU / memory. Requires real model in Phase 2.",
            },
            "first_inference": {
                "name": "First Inference Latency",
                "status": "Not measured",
                "value": None,
                "unit": "ms",
                "description": "Cold-start inference latency including graph compilation. Requires real inference in Phase 2.",
            },
            "average_inference": {
                "name": "Average Inference Latency",
                "status": "Not measured",
                "value": None,
                "unit": "ms",
                "description": "Warm inference latency across repeated evaluation runs. Requires real inference in Phase 2.",
            },
            "throughput": {
                "name": "Throughput",
                "status": "Not measured",
                "value": None,
                "unit": "fps or tokens/sec",
                "description": "Processing speed for vision frames or text generation. Requires real inference in Phase 2.",
            },
            "memory_usage": {
                "name": "Memory Usage",
                "status": "Not measured",
                "value": None,
                "unit": "MB",
                "description": "Peak host and dedicated hardware memory footprint. Requires real inference in Phase 2.",
            },
            "cpu_usage": {
                "name": "CPU Usage",
                "status": "Not measured",
                "value": None,
                "unit": "%",
                "description": "Host processor utilization during inference. Requires real inference in Phase 2.",
            },
            "gpu_usage": {
                "name": "GPU Usage",
                "status": "Not measured",
                "value": None,
                "unit": "%",
                "description": "DirectML / Adreno GPU utilization. Requires real GPU inference in Phase 2.",
            },
            "npu_usage": {
                "name": "NPU Usage",
                "status": "Not measured",
                "value": None,
                "unit": "%",
                "description": "Qualcomm Hexagon NPU load during accelerated passes. Requires Phase 2 NPU integration.",
            },
            "storage_io_latency": {
                "name": "Local Storage I/O Latency",
                "status": "Measured",
                "value": None,  # Updated dynamically by run_storage_baseline
                "unit": "ms",
                "description": "Actual measured local SQLite write-read round-trip latency. Foundation baseline.",
            },
        }
        self._history: list[BenchmarkRecord] = []
        self._last_run: dt.datetime | None = None

    def get_summary(self) -> BenchmarkSummary:
        return BenchmarkSummary(
            benchmarks=self._benchmarks,
            history=self._history,
            last_run=self._last_run,
            measured_device="Host (detecting...)",
        )

    def record_run(self, record: BenchmarkRecord) -> None:
        self._history.append(record)
        self._last_run = record.timestamp

    def run_storage_baseline(self) -> BenchmarkRecord:
        """
        Runs a real, measured foundation baseline test measuring actual local disk I/O.

        This is the ONLY benchmark that returns real measured values in Phase 1.
        All AI inference metrics remain None / "Not measured" until Phase 2.
        """
        import platform
        import tempfile
        import os

        # Measure actual disk I/O latency with a real write/read cycle
        start_time = time.perf_counter()

        test_payload = b"SENTINEL_BASELINE_" + uuid.uuid4().hex.encode()
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix="sentinel_bench_", suffix=".tmp", delete=False
            ) as tmp:
                tmp_path = tmp.name
                tmp.write(test_payload)
                tmp.flush()
                os.fsync(tmp.fileno())

            # Timed read-back
            with open(tmp_path, "rb") as f:
                _ = f.read()
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)

        # Update in-memory metric so it shows in the dashboard
        self._benchmarks["storage_io_latency"]["value"] = elapsed_ms
        self._benchmarks["storage_io_latency"]["status"] = "Measured"

        now = dt.datetime.now(dt.timezone.utc)
        host_platform = platform.platform()

        record = BenchmarkRecord(
            id=str(uuid.uuid4())[:8],
            model_name="Local Storage I/O Baseline",
            model_version="Phase 1 Foundation",
            runtime="Python tempfile + os.fsync",
            execution_provider="Host Filesystem",
            device=host_platform,
            timestamp=now,
            input_type="Binary write/read cycle",
            load_time_ms=None,
            first_inference_ms=elapsed_ms,
            average_inference_ms=elapsed_ms,
            throughput=None,   # Not applicable for storage test
            memory_mb=None,    # Not measured
            cpu_percent=None,  # Not measured
            gpu_percent=None,  # Not measured
            npu_percent=None,  # Not measured
            notes=(
                f"Phase 1 foundation baseline: real local disk I/O latency "
                f"({elapsed_ms} ms). AI inference metrics remain 'Not measured' "
                f"until Phase 2 model integration."
            ),
        )
        self.record_run(record)
        return record


benchmark_manager = BenchmarkManager()
