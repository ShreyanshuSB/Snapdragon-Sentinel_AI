from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ExecutionProviderState(str, Enum):
    NOT_INSTALLED = "NOT_INSTALLED"
    AVAILABLE = "AVAILABLE"
    SELECTABLE = "SELECTABLE"
    SELECTED = "SELECTED"
    RUNNING = "RUNNING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class VerificationMethod(str, Enum):
    NOT_TESTED = "NOT_TESTED"
    SYSTEM_DIAGNOSTIC = "SYSTEM_DIAGNOSTIC"
    MODEL_INFERENCE = "MODEL_INFERENCE"
    BENCHMARK = "BENCHMARK"


class ModelCompatibilityRating(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    LIKELY_COMPATIBLE = "LIKELY_COMPATIBLE"
    UNVERIFIED = "UNVERIFIED"
    INCOMPATIBLE = "INCOMPATIBLE"


class ProviderDiagnostics(BaseModel):
    name: str = Field(..., description="Provider identifier, e.g. QNNExecutionProvider")
    state: ExecutionProviderState = Field(..., description="Current state machine state")
    available: bool = Field(default=False, description="Whether package/provider is registered in runtime")
    selected: bool = Field(default=False, description="Whether provider is chosen as active provider")
    running: bool = Field(default=False, description="Whether active session is currently running on provider")
    verified: bool = Field(default=False, description="Whether actual inference on real hardware was verified")
    version: str | None = Field(default=None, description="Provider library version if discoverable")
    details: str = Field(default="", description="Technical rationale or error details")


class TargetProfile(BaseModel):
    target_platform: str = Field(..., description="Target platform name")
    target_cpu: str = Field(..., description="Target CPU name")
    target_gpu: str = Field(..., description="Target GPU name")
    target_npu: str = Field(..., description="Target NPU name and rating")
    target_architecture: str = Field(..., description="Target CPU architecture")
    target_os: str = Field(..., description="Target Operating System")
    preferred_runtime: str = Field(..., description="Target inference runtime")
    notes: str = Field(..., description="Target deployment description")


class HardwareDiagnosticsResponse(BaseModel):
    os_name: str = Field(..., description="Operating system name")
    os_version: str = Field(..., description="Operating system release and version")
    os_build: str = Field(..., description="Windows build number")
    system_architecture: str = Field(..., description="Host architecture (e.g. AMD64, ARM64)")
    processor_name: str = Field(..., description="Exact processor description from OS")
    processor_vendor: str = Field(..., description="Processor vendor identifier")
    processor_architecture: str = Field(..., description="Processor architecture")
    cpu_cores_physical: int | None = Field(default=None, description="Physical CPU cores")
    cpu_cores_logical: int | None = Field(default=None, description="Logical CPU cores")
    ram_total_gb: float = Field(..., description="Total installed RAM in GB")
    ram_available_gb: float = Field(..., description="Available RAM in GB")
    ram_used_percent: float = Field(..., description="RAM utilization percentage")
    gpus: list[str] = Field(default_factory=list, description="Detected display adapters/GPUs")
    npu_detected: bool = Field(default=False, description="Whether NPU hardware device is present in OS")
    npu_device_name: str | None = Field(default=None, description="Exact NPU device name if detected")
    machine_manufacturer: str | None = Field(default=None, description="System manufacturer")
    machine_model: str | None = Field(default=None, description="System product model")
    snapdragon_detected: bool = Field(default=False, description="Whether host is confirmed Qualcomm Snapdragon")
    snapdragon_platform: str = Field(default="NONE", description="Chipset identifier or UNKNOWN or NONE")
    is_development_host: bool = Field(default=True, description="True if host is dev machine rather than production target")
    target_comparison: str = Field(..., description="Explicit comparison of current machine against target deployment")


class MissingDependency(BaseModel):
    name: str
    why_needed: str
    how_used: str
    installation_status: str


class RuntimeDiagnosticsResponse(BaseModel):
    python_version: str
    onnxruntime_installed: bool
    onnxruntime_version: str | None
    available_providers: list[str]
    qnn_available: bool
    directml_available: bool
    cpu_available: bool
    cuda_available: bool
    selected_provider: str
    qnn_version: str | None
    provider_states: dict[str, ProviderDiagnostics]
    npu_detected: bool
    npu_execution_verified: bool = Field(default=False, description="Strictly false until proven by real model execution")
    verification_method: VerificationMethod = Field(default=VerificationMethod.NOT_TESTED)
    missing_dependencies: list[MissingDependency] = Field(default_factory=list)


class FullDiagnosticsResponse(BaseModel):
    hardware: HardwareDiagnosticsResponse
    runtime: RuntimeDiagnosticsResponse
    target_profile: TargetProfile
    summary: str


class ReferenceMetrics(BaseModel):
    reference_latency_ms: float | None = None
    reference_throughput_fps: float | None = None
    reference_device: str = "Snapdragon X Elite Reference Device (Qualcomm AI Hub)"
    reference_source: str = "Qualcomm AI Hub"


class MeasuredMetrics(BaseModel):
    our_latency_ms: float | None = None
    our_throughput_fps: float | None = None
    our_device: str | None = None
    measured_timestamp: str | None = None


class ModelCandidateRecord(BaseModel):
    id: str
    name: str
    version: str
    task: str
    source: str
    license: str
    format: str
    input_modalities: list[str]
    output_modalities: list[str]
    input_width: int
    input_height: int
    quantization: str
    parameter_count: str
    supported_chipsets: list[str]
    supported_runtimes: list[str]
    preferred_execution_provider: str
    status: str
    reference_metrics: ReferenceMetrics
    our_metrics: MeasuredMetrics
    official_hub_url: str
    export_method: str


class ModelEvaluationResult(BaseModel):
    model_id: str
    name: str
    compatibility: ModelCompatibilityRating
    hardware_compatibility: str
    runtime_compatibility: str
    provider_compatibility: str
    input_compatibility: str
    license_status: str
    verification_status: str
    technical_notes: str


class ModelSelectionResponse(BaseModel):
    target_hardware: str
    current_hardware: str
    active_runtime: str
    candidates: list[ModelEvaluationResult]
    recommended_first_candidate: str
    selection_rationale: str
    next_steps: list[str]
