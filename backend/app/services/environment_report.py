from __future__ import annotations

import sys
from app.ai.model_registry import model_registry
from app.ai.model_selector import model_selector
from app.services.hardware_diagnostics import hardware_diagnostics
from app.services.runtime_diagnostics import runtime_diagnostics


def generate_environment_report() -> str:
    """
    Generates a truthful, human-readable SENTINEL AI Environment Report.
    No fabricated values. Strictly reports measured and discovered telemetry.
    """
    hw = hardware_diagnostics.get_diagnostics()
    rt = runtime_diagnostics.get_diagnostics()
    target = hardware_diagnostics.load_target_profile()
    selection = model_selector.select_first_candidate(hw, rt)

    ready_for_model = "YES (Development CPU fallback / Staging ready)" if rt.onnxruntime_installed else "NO (ONNX Runtime required)"

    qnn_status = "Available" if rt.qnn_available else "Not Installed"
    dml_status = "Available" if rt.directml_available else "Not Installed"
    cpu_status = "Available" if rt.cpu_available else "Not Installed"

    npu_status = hw.npu_device_name if hw.npu_detected else "Not Detected"
    npu_verification = "VERIFIED" if rt.npu_execution_verified else "NOT VERIFIED"

    snapdragon_status = (
        f"Detected ({hw.snapdragon_platform})"
        if hw.snapdragon_detected
        else "Not Detected (Development Host)"
    )

    gpus_str = ", ".join(hw.gpus) if hw.gpus else "None detected"

    report_lines = [
        "============================================================",
        "              SENTINEL AI ENVIRONMENT REPORT               ",
        "============================================================",
        "",
        "Hardware",
        "---------",
        f"Processor:    {hw.processor_name}",
        f"Vendor:       {hw.processor_vendor}",
        f"Architecture: {hw.system_architecture}",
        f"RAM:          {hw.ram_total_gb:.2f} GB Total ({hw.ram_available_gb:.2f} GB Available, {hw.ram_used_percent:.0f}% Used)",
        f"GPU:          {gpus_str}",
        f"NPU:          {npu_status}",
        f"Host Machine: {hw.machine_manufacturer or 'Unknown'} {hw.machine_model or ''}".strip(),
        "",
        "Runtime",
        "-------",
        f"Python:       {rt.python_version}",
        f"ONNX Runtime: {rt.onnxruntime_version or 'Not Installed'}",
        f"QNN:          {qnn_status}",
        f"DirectML:     {dml_status}",
        "",
        "Execution Providers",
        "-------------------",
        f"CPU:          {cpu_status} (State: {rt.provider_states.get('CPUExecutionProvider', {}).state.value if 'CPUExecutionProvider' in rt.provider_states else 'UNKNOWN'})",
        f"QNN:          {qnn_status} (State: {rt.provider_states.get('QNNExecutionProvider', {}).state.value if 'QNNExecutionProvider' in rt.provider_states else 'UNKNOWN'})",
        f"DirectML:     {dml_status} (State: {rt.provider_states.get('DmlExecutionProvider', {}).state.value if 'DmlExecutionProvider' in rt.provider_states else 'UNKNOWN'})",
        f"Selected:     {rt.selected_provider}",
        "",
        "Snapdragon",
        "----------",
        f"Detected:     {snapdragon_status}",
        f"Verification: {npu_verification}",
        f"Notes:        {hw.target_comparison}",
        "",
        "Vision Model Candidates",
        "-----------------------",
    ]

    for candidate in selection.candidates:
        report_lines.append(
            f"{candidate.name:14}: {candidate.compatibility.value:18} | {candidate.license_status.split('.')[0]}"
        )

    report_lines.extend([
        "",
        "Target Platform",
        "---------------",
        f"Platform:     {target.target_platform}",
        f"CPU Target:   {target.target_cpu}",
        f"NPU Target:   {target.target_npu}",
        f"Preferred RT: {target.preferred_runtime}",
        "",
        f"Recommended First Model: {selection.recommended_first_candidate.upper()}",
        f"Ready for model integration: {ready_for_model}",
        "============================================================",
    ])

    return "\n".join(report_lines)


if __name__ == "__main__":
    print(generate_environment_report())
