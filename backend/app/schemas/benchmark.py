from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BenchmarkRecord(BaseModel):
    id: str
    model_name: str
    model_version: str
    runtime: str
    execution_provider: str
    device: str
    timestamp: datetime
    input_type: str
    load_time_ms: float | None = None
    first_inference_ms: float | None = None
    average_inference_ms: float | None = None
    preprocess_ms: float | None = None
    postprocess_ms: float | None = None
    total_pipeline_ms: float | None = None
    cold_warm: str = "warm"
    throughput: float | None = None
    memory_mb: float | None = None
    cpu_percent: float | None = None
    gpu_percent: float | None = None
    npu_percent: float | None = None
    notes: str = ""

    model_config = ConfigDict(from_attributes=True)


class BenchmarkSummary(BaseModel):
    benchmarks: dict[str, dict[str, Any]]
    history: list[BenchmarkRecord]
    last_run: datetime | None = None
    measured_device: str = "Snapdragon/Windows Host"
