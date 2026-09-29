from __future__ import annotations

import logging
from app.ai.model_registry import model_registry
from app.schemas.diagnostics import (
    HardwareDiagnosticsResponse,
    ModelCandidateRecord,
    ModelCompatibilityRating,
    ModelEvaluationResult,
    ModelSelectionResponse,
    RuntimeDiagnosticsResponse,
    TargetProfile,
)
from app.services.hardware_diagnostics import hardware_diagnostics
from app.services.runtime_diagnostics import runtime_diagnostics

logger = logging.getLogger("sentinel.model_selector")


class ModelSelector:
    """
    Evaluates vision model candidates against hardware and runtime capabilities.
    Does NOT use subjective rankings or scores.
    Outputs strict technical compatibility matrices.
    """

    def evaluate_candidate(
        self,
        candidate: ModelCandidateRecord,
        hw: HardwareDiagnosticsResponse,
        runtime: RuntimeDiagnosticsResponse,
        target: TargetProfile,
    ) -> ModelEvaluationResult:
        # 1. Hardware compatibility
        if hw.snapdragon_detected:
            hw_compat = f"Directly compatible with detected host {hw.snapdragon_platform} and target {target.target_cpu}."
        else:
            hw_compat = (
                f"Supported via CPU fallback on host {hw.processor_name} ({hw.system_architecture}). "
                f"Full acceleration targets Snapdragon Copilot+ PC ({target.target_architecture})."
            )

        # 2. Runtime compatibility
        if runtime.onnxruntime_installed:
            rt_compat = f"Compatible with ONNX Runtime v{runtime.onnxruntime_version}. ONNX format supported."
        else:
            rt_compat = "Inference runtime not installed. ONNX Runtime package required."

        # 3. Provider compatibility
        if runtime.qnn_available:
            prov_compat = "Target provider QNNExecutionProvider is active and registered."
        elif runtime.cpu_available:
            prov_compat = (
                "QNNExecutionProvider not present on host. "
                "Compatible with host CPUExecutionProvider as development fallback."
            )
        else:
            prov_compat = "No compatible execution provider registered in current runtime."

        # 4. Input compatibility
        input_compat = (
            f"Standard RGB image ({candidate.input_width}x{candidate.input_height}x3). "
            f"Compatible with SENTINEL frame capture pipeline."
        )

        # 5. License status
        if candidate.license == "Apache-2.0":
            lic_status = "Permissive (Apache-2.0). Suitable for private and commercial deployment without copyleft restrictions."
        elif candidate.license == "AGPL-3.0":
            lic_status = "Copyleft (AGPL-3.0). Strong copyleft licensing requires careful compliance for network distribution."
        else:
            lic_status = f"License: {candidate.license}"

        # 6. Overall Technical Rating
        if not runtime.onnxruntime_installed:
            rating = ModelCompatibilityRating.UNVERIFIED
        elif runtime.qnn_available:
            rating = ModelCompatibilityRating.COMPATIBLE
        elif runtime.cpu_available:
            # Compatible via development fallback
            rating = ModelCompatibilityRating.LIKELY_COMPATIBLE
        else:
            rating = ModelCompatibilityRating.INCOMPATIBLE

        return ModelEvaluationResult(
            model_id=candidate.id,
            name=candidate.name,
            compatibility=rating,
            hardware_compatibility=hw_compat,
            runtime_compatibility=rt_compat,
            provider_compatibility=prov_compat,
            input_compatibility=input_compat,
            license_status=lic_status,
            verification_status="NOT_VERIFIED (Pending real inference test in Phase 2B)",
            technical_notes=(
                f"Qualcomm AI Hub Reference Device Latency: {candidate.reference_metrics.reference_latency_ms} ms. "
                f"Host inference measurement pending model integration."
            ),
        )

    def select_first_candidate(
        self,
        hw: HardwareDiagnosticsResponse | None = None,
        runtime: RuntimeDiagnosticsResponse | None = None,
    ) -> ModelSelectionResponse:
        if hw is None:
            hw = hardware_diagnostics.get_diagnostics()
        if runtime is None:
            runtime = runtime_diagnostics.get_diagnostics()
        target = hardware_diagnostics.load_target_profile()

        candidates = model_registry.list_candidates()
        evaluations = [
            self.evaluate_candidate(c, hw, runtime, target) for c in candidates
        ]

        # Engineering selection criteria for first model:
        # 1. Official Qualcomm AI Hub Windows Reference: YOLO-X is the canonical detector in
        #    Qualcomm's Windows C++ / Python object detection sample.
        # 2. Permissive License: Apache-2.0 avoids AGPL-3.0 viral copyleft obligations.
        # 3. Predictable Input/Output: Clean bounding box [x1, y1, x2, y2] + classification head.
        # 4. Multi-tier footprint: Nano (0.9M) to Small (9.0M) allows testing on dev CPU and Snapdragon NPU.

        recommended = "yolo-x"
        rationale = (
            "YOLO-X is selected as the first vision model candidate based on explicit engineering criteria: "
            "(1) It is the primary model used in Qualcomm's official Windows Object Detection reference sample "
            "(object_detection_windows_cpp) on AI Hub; "
            "(2) It is licensed under Apache 2.0 (permissive, avoiding the AGPL-3.0 copyleft restrictions of YOLOv8/v10/v11); "
            "(3) It has an established ONNX graph export path verified by Qualcomm AI Hub with direct QNN EP compatibility; "
            "(4) It provides a clean fallback to CPUExecutionProvider on development machines while targeting Qualcomm Hexagon NPU."
        )

        next_steps = [
            "1. Download or compile official YOLO-X ONNX model artifact into models/vision/yolox.onnx.",
            "2. Implement VisionModelAdapter and ONNX Runtime session loader.",
            "3. Run real single-frame inference test to measure actual cold-start and warm inference latency.",
            "4. Verify detection accuracy against sample workspace image frames.",
            "5. Mark QNN execution verified ONLY when executed on real Snapdragon hardware.",
        ]

        return ModelSelectionResponse(
            target_hardware=f"{target.target_platform} ({target.target_cpu})",
            current_hardware=f"{hw.processor_name} ({hw.system_architecture})",
            active_runtime=(
                f"ONNX Runtime v{runtime.onnxruntime_version} "
                f"[Selected Provider: {runtime.selected_provider}]"
                if runtime.onnxruntime_installed
                else "ONNX Runtime Not Installed"
            ),
            candidates=evaluations,
            recommended_first_candidate=recommended,
            selection_rationale=rationale,
            next_steps=next_steps,
        )


model_selector = ModelSelector()
