from __future__ import annotations

import pytest
from app.schemas.diagnostics import ExecutionProviderState, VerificationMethod
from app.services.runtime_diagnostics import (
    AIRuntimeDiagnostics,
    ExecutionProviderStateMachine,
)


def test_real_runtime_diagnostics() -> None:
    diag = AIRuntimeDiagnostics().get_diagnostics()

    assert diag.python_version is not None
    assert diag.onnxruntime_installed is True
    assert diag.onnxruntime_version is not None
    assert isinstance(diag.available_providers, list)
    assert "CPUExecutionProvider" in diag.available_providers
    # Real host without QNN packages
    assert diag.qnn_available is False
    assert diag.selected_provider in ["CPUExecutionProvider", "QNNExecutionProvider", "DmlExecutionProvider"]
    # Critical verification constraints
    assert diag.npu_execution_verified is False
    assert diag.verification_method == VerificationMethod.NOT_TESTED


def test_execution_provider_state_machine_valid_transitions() -> None:
    sm = ExecutionProviderStateMachine()

    # NOT_INSTALLED -> AVAILABLE
    s1 = sm.transition(ExecutionProviderState.NOT_INSTALLED, ExecutionProviderState.AVAILABLE)
    assert s1 == ExecutionProviderState.AVAILABLE

    # AVAILABLE -> SELECTABLE
    s2 = sm.transition(s1, ExecutionProviderState.SELECTABLE)
    assert s2 == ExecutionProviderState.SELECTABLE

    # SELECTABLE -> SELECTED
    s3 = sm.transition(s2, ExecutionProviderState.SELECTED)
    assert s3 == ExecutionProviderState.SELECTED

    # SELECTED -> RUNNING
    s4 = sm.transition(s3, ExecutionProviderState.RUNNING)
    assert s4 == ExecutionProviderState.RUNNING

    # RUNNING -> VERIFIED
    s5 = sm.transition(s4, ExecutionProviderState.VERIFIED)
    assert s5 == ExecutionProviderState.VERIFIED


def test_execution_provider_state_machine_invalid_transitions() -> None:
    sm = ExecutionProviderStateMachine()

    # Cannot transition directly from NOT_INSTALLED to VERIFIED
    with pytest.raises(ValueError, match="Invalid execution provider state transition"):
        sm.transition(ExecutionProviderState.NOT_INSTALLED, ExecutionProviderState.VERIFIED)

    # Cannot transition directly from AVAILABLE to VERIFIED without running inference
    with pytest.raises(ValueError, match="Invalid execution provider state transition"):
        sm.transition(ExecutionProviderState.AVAILABLE, ExecutionProviderState.VERIFIED)

    # Cannot transition from SELECTED to VERIFIED without RUNNING
    with pytest.raises(ValueError, match="Invalid execution provider state transition"):
        sm.transition(ExecutionProviderState.SELECTED, ExecutionProviderState.VERIFIED)


def test_missing_runtime_diagnostics_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    service = AIRuntimeDiagnostics()
    monkeypatch.setattr(service, "probe_onnxruntime", lambda: (False, None, []))

    diag = service.get_diagnostics()
    assert diag.onnxruntime_installed is False
    assert diag.onnxruntime_version is None
    assert diag.available_providers == []
    assert diag.selected_provider == "NONE"
    assert any(m.name == "onnxruntime" for m in diag.missing_dependencies)
