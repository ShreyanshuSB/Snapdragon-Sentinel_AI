from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ApiError(BaseModel):
    detail: str = Field(..., description="Error message detail")
    code: str | None = Field(default=None, description="Optional error code")


class RuntimeStatus(BaseModel):
    runtime_name: str = Field(default="Not connected", description="Inference engine name")
    execution_provider: str = Field(default="Not configured", description="Active execution provider")
    device_target: str = Field(..., description="Target OS and architecture")
    local_inference_policy: str = Field(default="Enabled (Local-only mode)", description="Configured local policy")
    model_connection: str = Field(default="Not connected", description="Real model connection status")
    npu_status: str = Field(default="Not verified", description="NPU execution verification state")
    hardware_acceleration: str = Field(
        default="Pending runtime verification",
        description="Whether acceleration was verified in benchmark/inference",
    )
    arm_architecture_detected: str = Field(..., description="Whether ARM architecture is present")


class HardwareStatus(BaseModel):
    platform: str
    processor: str
    architecture: str
    python_version: str
    cpu_cores: str
    gpu: str = "Not verified"
    npu: str = "Not verified"


class ModelStatus(BaseModel):
    name: str
    role: str
    version: str = "Not measured"
    source: str = "Not configured"
    status: str = "PLANNED"  # PLANNED, CANDIDATE, AVAILABLE, LOADING, READY, RUNNING, VERIFIED, FAILED, NOT_AVAILABLE, NOT_VERIFIED
    availability: str = "NOT_AVAILABLE"
    runtime: str = "Not connected"
    execution_provider: str = "Not configured"
    current_device: str = "Not connected"
    target_device: str = "Snapdragon X-series / Qualcomm NPU"
    current_verification: str = "NOT_VERIFIED"
    npu_verification: str = "NOT_VERIFIED"
    quantization: str = "Pending Phase 2+"
    model_size: str = "Not loaded"
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    hub_compatible: bool = True

    # Backwards compatibility aliases
    device: str = "Not connected"
    verified_device: str = "Not verified"
    parameters: str = "Not loaded"
    available: bool = False


class ModelStatusResponse(BaseModel):
    models: dict[str, ModelStatus]
    runtime: RuntimeStatus
    hardware: HardwareStatus
