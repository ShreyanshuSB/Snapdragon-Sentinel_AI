from __future__ import annotations

import logging
import platform
import sys
from typing import Any

from app.schemas.diagnostics import (
    ExecutionProviderState,
    MissingDependency,
    ProviderDiagnostics,
    RuntimeDiagnosticsResponse,
    VerificationMethod,
)
from app.services.hardware_diagnostics import hardware_diagnostics

logger = logging.getLogger("sentinel.runtime_diagnostics")


class ExecutionProviderStateMachine:
    """
    Manages and validates execution provider lifecycle states.
    Valid states: NOT_INSTALLED, AVAILABLE, SELECTABLE, SELECTED, RUNNING, VERIFIED, FAILED, UNKNOWN.
    Enforces that VERIFIED cannot be reached without an actual hardware inference test.
    """

    VALID_TRANSITIONS: dict[ExecutionProviderState, set[ExecutionProviderState]] = {
        ExecutionProviderState.NOT_INSTALLED: {ExecutionProviderState.AVAILABLE, ExecutionProviderState.FAILED},
        ExecutionProviderState.AVAILABLE: {ExecutionProviderState.SELECTABLE, ExecutionProviderState.NOT_INSTALLED, ExecutionProviderState.FAILED},
        ExecutionProviderState.SELECTABLE: {ExecutionProviderState.SELECTED, ExecutionProviderState.AVAILABLE, ExecutionProviderState.FAILED},
        ExecutionProviderState.SELECTED: {ExecutionProviderState.RUNNING, ExecutionProviderState.SELECTABLE, ExecutionProviderState.FAILED},
        ExecutionProviderState.RUNNING: {ExecutionProviderState.VERIFIED, ExecutionProviderState.SELECTED, ExecutionProviderState.FAILED},
        ExecutionProviderState.VERIFIED: {ExecutionProviderState.RUNNING, ExecutionProviderState.FAILED},
        ExecutionProviderState.FAILED: {ExecutionProviderState.NOT_INSTALLED, ExecutionProviderState.AVAILABLE},
        ExecutionProviderState.UNKNOWN: {ExecutionProviderState.NOT_INSTALLED, ExecutionProviderState.AVAILABLE},
    }

    @classmethod
    def can_transition(cls, from_state: ExecutionProviderState, to_state: ExecutionProviderState) -> bool:
        allowed = cls.VALID_TRANSITIONS.get(from_state, set())
        return to_state in allowed

    @classmethod
    def transition(
        cls, current: ExecutionProviderState, new_state: ExecutionProviderState
    ) -> ExecutionProviderState:
        if current == new_state:
            return current
        if not cls.can_transition(current, new_state):
            raise ValueError(
                f"Invalid execution provider state transition: {current.value} -> {new_state.value}. "
                f"VERIFIED requires an actual supported model inference test."
            )
        return new_state


class AIRuntimeDiagnostics:
    """
    Discovers AI runtime packages and execution provider capabilities.
    Validates onnxruntime, QNN, DirectML, and CPU execution providers.
    """

    def __init__(self) -> None:
        self._qnn_verified: bool = False
        self._verification_method: VerificationMethod = VerificationMethod.NOT_TESTED

    def probe_onnxruntime(self) -> tuple[bool, str | None, list[str]]:
        try:
            import onnxruntime as ort
            version = str(getattr(ort, "__version__", "unknown"))
            providers = ort.get_available_providers()
            return True, version, list(providers)
        except ImportError:
            return False, None, []
        except Exception as e:
            logger.warning("Error inspecting onnxruntime: %s", e)
            return False, None, []

    def probe_qnn_version(self) -> str | None:
        """
        Attempts to read QNN SDK / runtime version if available on disk or module.
        """
        try:
            # Check environment or sys.modules for qnn
            import os
            qnn_sdk_root = os.environ.get("QNN_SDK_ROOT")
            if qnn_sdk_root:
                version_file = os.path.join(qnn_sdk_root, "version.txt")
                if os.path.exists(version_file):
                    with open(version_file, "r", encoding="utf-8") as f:
                        return f.read().strip()
            return None
        except Exception:
            return None

    def build_provider_diagnostics(
        self,
        name: str,
        available: bool,
        is_selected: bool,
        details: str,
        version: str | None = None,
    ) -> ProviderDiagnostics:
        state = ExecutionProviderState.NOT_INSTALLED
        if available:
            state = ExecutionProviderState.AVAILABLE
            if is_selected:
                state = ExecutionProviderState.SELECTED

        return ProviderDiagnostics(
            name=name,
            state=state,
            available=available,
            selected=is_selected,
            running=False,
            verified=False,  # Strictly false in this phase
            version=version,
            details=details,
        )

    def get_diagnostics(self) -> RuntimeDiagnosticsResponse:
        ort_installed, ort_version, providers = self.probe_onnxruntime()

        qnn_available = "QNNExecutionProvider" in providers
        dml_available = "DmlExecutionProvider" in providers
        cpu_available = "CPUExecutionProvider" in providers
        cuda_available = "CUDAExecutionProvider" in providers

        # Determine default selected provider
        if qnn_available:
            selected_provider = "QNNExecutionProvider"
        elif dml_available:
            selected_provider = "DmlExecutionProvider"
        elif cpu_available:
            selected_provider = "CPUExecutionProvider"
        else:
            selected_provider = "NONE"

        qnn_version = self.probe_qnn_version()

        # Build provider state tracking
        provider_states: dict[str, ProviderDiagnostics] = {}

        # QNN
        provider_states["QNNExecutionProvider"] = self.build_provider_diagnostics(
            name="QNNExecutionProvider",
            available=qnn_available,
            is_selected=(selected_provider == "QNNExecutionProvider"),
            version=qnn_version,
            details=(
                "Qualcomm AI Engine Direct (QNN) Execution Provider for Hexagon NPU. "
                + ("Available in ONNX Runtime." if qnn_available else "Not installed on this host environment.")
            ),
        )

        # DirectML
        provider_states["DmlExecutionProvider"] = self.build_provider_diagnostics(
            name="DmlExecutionProvider",
            available=dml_available,
            is_selected=(selected_provider == "DmlExecutionProvider"),
            details=(
                "DirectML Execution Provider for hardware-accelerated Windows DirectX 12 GPUs/NPUs. "
                + ("Available." if dml_available else "Not installed in this environment.")
            ),
        )

        # CPU
        provider_states["CPUExecutionProvider"] = self.build_provider_diagnostics(
            name="CPUExecutionProvider",
            available=cpu_available,
            is_selected=(selected_provider == "CPUExecutionProvider"),
            details="Standard CPU Execution Provider (host processor fallback).",
        )

        # Host hardware NPU detection status
        hw = hardware_diagnostics.get_diagnostics()
        npu_detected = hw.npu_detected

        # Missing dependencies analysis
        missing: list[MissingDependency] = []
        if not ort_installed:
            missing.append(
                MissingDependency(
                    name="onnxruntime",
                    why_needed="Core local inference runtime for running ONNX models without remote cloud dependencies.",
                    how_used="Loads and evaluates vision models (YOLO-X) locally on CPU, GPU, or NPU.",
                    installation_status="NOT_INSTALLED",
                )
            )

        if not qnn_available:
            missing.append(
                MissingDependency(
                    name="onnxruntime-qnn / QNN Execution Provider",
                    why_needed="Qualcomm Neural Processing SDK provider required for Snapdragon Hexagon NPU offloading.",
                    how_used="Compiles and executes ONNX subgraphs directly on the Hexagon NPU via Qualcomm AI Engine Direct.",
                    installation_status="NOT_INSTALLED (Target Hardware Deployment Pending)",
                )
            )

        return RuntimeDiagnosticsResponse(
            python_version=sys.version.split()[0],
            onnxruntime_installed=ort_installed,
            onnxruntime_version=ort_version,
            available_providers=providers,
            qnn_available=qnn_available,
            directml_available=dml_available,
            cpu_available=cpu_available,
            cuda_available=cuda_available,
            selected_provider=selected_provider,
            qnn_version=qnn_version,
            provider_states=provider_states,
            npu_detected=npu_detected,
            npu_execution_verified=False,  # Strictly False until real inference test
            verification_method=VerificationMethod.NOT_TESTED,
            missing_dependencies=missing,
        )


runtime_diagnostics = AIRuntimeDiagnostics()
