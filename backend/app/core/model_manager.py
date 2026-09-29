from __future__ import annotations

import platform
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ModelMeta:
    name: str
    role: str
    version: str = "Not measured"
    source: str = "Not configured"
    status: str = "PLANNED"  # PLANNED, CANDIDATE, AVAILABLE, LOADING, READY, RUNNING, VERIFIED, FAILED, NOT_AVAILABLE, NOT_VERIFIED
    availability: str = "NOT_AVAILABLE"
    runtime: str = "Not connected"
    execution_provider: str = "Not configured"
    current_device: str = "Not connected"
    target_device: str = "Snapdragon X Elite NPU (Hexagon)"
    current_verification: str = "NOT_VERIFIED"
    npu_verification: str = "NOT_VERIFIED"
    quantization: str = "Pending Phase 2+"
    model_size: str = "Not loaded"
    description: str = ""
    metadata: dict[str, Any] = None
    hub_compatible: bool = True

    # Backwards compatibility aliases
    device: str = "Not connected"
    verified_device: str = "Not verified"
    parameters: str = "Not loaded"
    available: bool = False

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.device or self.device == "Not connected":
            self.device = self.current_device
        if not self.verified_device or self.verified_device == "Not verified":
            self.verified_device = self.current_verification
        if not self.parameters or self.parameters == "Not loaded":
            self.parameters = self.model_size
        if self.status in ("AVAILABLE", "READY", "RUNNING", "VERIFIED"):
            self.available = True
            self.availability = "AVAILABLE"


class ModelManager:
    def __init__(self) -> None:
        self._models: dict[str, ModelMeta] = {
            "vision": ModelMeta(
                name="YOLO-X Small",
                role="Workspace Object & Scene Understanding",
                version="Small (640x640)",
                source="Qualcomm AI Hub / Megvii YOLO-X",
                status="AVAILABLE",
                availability="AVAILABLE",
                runtime="ONNX Runtime v1.30.0",
                execution_provider="CPUExecutionProvider",
                current_device="Host CPU",
                target_device="Snapdragon X Elite NPU (Hexagon)",
                current_verification="Host CPU Verified",
                npu_verification="NOT_VERIFIED",
                quantization="FP32 ONNX Export (INT8 Target Configured)",
                model_size="9.0M parameters",
                description="Qualcomm AI Hub-optimized YOLO-X detector for physical desk objects and peripherals.",
                hub_compatible=True,
                available=True,
                device="Host CPU",
                verified_device="Host CPU Verified",
                parameters="9.0M parameters",
            ),
            "ocr": ModelMeta(
                name="EasyOCR (CRAFT + CRNN)",
                role="Text & Document Ingestion",
                version="CRAFT + CRNN",
                source="Local CRAFT Text Detector & CRNN Recognizer",
                status="AVAILABLE",
                availability="AVAILABLE",
                runtime="Local PyTorch Engine (CPU Fallback)",
                execution_provider="CPUExecutionProvider",
                current_device="Host CPU",
                target_device="Snapdragon X Elite NPU (QNN)",
                current_verification="Host CPU Verified",
                npu_verification="NOT_VERIFIED",
                quantization="FP32 / INT8 Target",
                model_size="24.6M parameters",
                description="Local text detection and recognition for physical labels, schematics, and documents.",
                hub_compatible=True,
                available=True,
                device="Host CPU",
                verified_device="Host CPU Verified",
                parameters="24.6M parameters",
            ),
            "speech": ModelMeta(
                name="Speech Engine",
                role="Local Voice Transcription",
                version="Planned Phase 4",
                source="OpenAI Whisper / Qualcomm AI Hub Target",
                status="PLANNED",
                availability="NOT_AVAILABLE",
                runtime="Not connected",
                execution_provider="Not configured",
                current_device="Not connected",
                target_device="Qualcomm QNN / CPU",
                current_verification="NOT_VERIFIED",
                npu_verification="NOT_VERIFIED",
                quantization="INT8 (Target)",
                model_size="74M params (Planned)",
                description="Designed for private on-device voice capture and intent transcription (Phase 4 roadmap).",
                hub_compatible=True,
                available=False,
                device="Not connected",
                verified_device="Not verified",
                parameters="Not loaded",
            ),
            "multimodal": ModelMeta(
                name="Multimodal Reasoning Engine",
                role="Vision + Voice + Memory Reasoning",
                version="Planned Phase 5",
                source="Qwen / Qualcomm AI Hub Target",
                status="PLANNED",
                availability="NOT_AVAILABLE",
                runtime="Not connected",
                execution_provider="Not configured",
                current_device="Not connected",
                target_device="Snapdragon NPU / GPU",
                current_verification="NOT_VERIFIED",
                npu_verification="NOT_VERIFIED",
                quantization="W4A16 / INT4 (Target)",
                model_size="3B params (Planned)",
                description="Unified multimodal reasoning connecting physical desk context with personal knowledge base (Phase 5 roadmap).",
                hub_compatible=True,
                available=False,
                device="Not connected",
                verified_device="Not verified",
                parameters="Not loaded",
            ),
            "embedding": ModelMeta(
                name="Embedding Engine",
                role="Semantic Memory Retrieval",
                version="Planned Phase 6",
                source="Sentence-Transformers / Qualcomm AI Hub Target",
                status="PLANNED",
                availability="NOT_AVAILABLE",
                runtime="Not connected",
                execution_provider="Not configured",
                current_device="Not connected",
                target_device="Qualcomm QNN / CPU",
                current_verification="NOT_VERIFIED",
                npu_verification="NOT_VERIFIED",
                quantization="FP16 / INT8 (Target)",
                model_size="22.7M params (Planned)",
                description="Dense local vector representation for high-speed local memory similarity search (Phase 6 roadmap).",
                hub_compatible=True,
                available=False,
                device="Not connected",
                verified_device="Not verified",
                parameters="Not loaded",
            ),
        }

    def report_model_status(self) -> dict[str, Any]:
        # Dynamically sync vision model status from real inference_engine
        try:
            from app.ai.vision.inference_engine import inference_engine
            is_loaded = inference_engine.runtime_adapter.is_loaded()
            weights_exist = inference_engine.model_path.exists()
            active_provider = inference_engine.runtime_adapter.get_active_provider() if is_loaded else "CPUExecutionProvider"

            self._models["vision"] = ModelMeta(
                name="YOLO-X Small",
                role="Workspace Object & Scene Understanding",
                version="Small (640x640)",
                source="Qualcomm AI Hub / Megvii YOLO-X",
                status="READY" if is_loaded else ("AVAILABLE" if weights_exist else "NOT_AVAILABLE"),
                availability="AVAILABLE" if weights_exist else "NOT_AVAILABLE",
                runtime="ONNX Runtime v1.30.0",
                execution_provider=active_provider,
                current_device="Host CPU",
                target_device="Snapdragon X Elite NPU (Hexagon)",
                current_verification="Host CPU Verified",
                npu_verification="NOT_VERIFIED",
                quantization="FP32 ONNX Export (INT8 Target Configured)",
                model_size="9.0M parameters",
                description="Qualcomm AI Hub-optimized YOLO-X detector for physical desk objects and peripherals.",
                hub_compatible=True,
                available=weights_exist,
                device="Host CPU",
                verified_device="Host CPU Verified",
                parameters="9.0M parameters",
            )
        except Exception:
            pass

        # Dynamically sync OCR model status from real ocr_engine
        try:
            from app.ai.ocr.ocr_engine import ocr_engine
            ocr_status = ocr_engine.get_status()
            if ocr_status.is_available:
                self._models["ocr"] = ModelMeta(
                    name=ocr_status.model_name,
                    role="Text & Document Ingestion",
                    version="CRAFT + CRNN",
                    source="Local CRAFT Text Detector & CRNN Recognizer",
                    status="READY" if ocr_status.is_loaded else "AVAILABLE",
                    availability="AVAILABLE",
                    runtime=ocr_status.runtime,
                    execution_provider="CPUExecutionProvider",
                    current_device="Host CPU",
                    target_device="Snapdragon X Elite NPU (QNN)",
                    current_verification="Host CPU Verified",
                    npu_verification="NOT_VERIFIED",
                    quantization="FP32 / INT8 Target",
                    model_size="24.6M parameters",
                    description="Qualcomm AI Hub-referenced CRAFT text detector and CRNN character recognizer for physical desk labels, schematics, and documents.",
                    hub_compatible=True,
                    available=True,
                    device="Host CPU",
                    verified_device="Host CPU Verified",
                    parameters="24.6M parameters",
                )
        except Exception:
            pass

        return {
            "models": {k: asdict(v) for k, v in self._models.items()},
            "runtime": self.report_runtime(),
            "hardware": self.report_hardware(),
        }

    def report_runtime(self) -> dict[str, str]:
        from app.services.runtime_diagnostics import runtime_diagnostics
        rt = runtime_diagnostics.get_diagnostics()
        target_arch = platform.machine()
        is_arm = "arm" in target_arch.lower()

        # Check real vision pipeline connection
        model_conn = "Not connected"
        try:
            from app.ai.vision.inference_engine import inference_engine
            if inference_engine.is_ready():
                model_conn = "Connected & Loaded (YOLO-X)"
            elif inference_engine.is_available():
                model_conn = "Available (YOLO-X)"
        except Exception:
            pass

        return {
            "runtime_name": f"ONNX Runtime v{rt.onnxruntime_version}" if rt.onnxruntime_installed else "Not installed",
            "execution_provider": rt.selected_provider,
            "device_target": f"Windows {target_arch}" if target_arch else "Windows Host",
            "local_inference_policy": "Enabled (Strict Local-only mode)",
            "model_connection": model_conn,
            "npu_status": "Verified" if rt.npu_execution_verified else "Not verified",
            "hardware_acceleration": f"Provider active: {rt.selected_provider}" if rt.cpu_available or rt.qnn_available else "Pending runtime verification",
            "arm_architecture_detected": "Yes" if is_arm else "No (x86_64 Host)",
        }

    def report_hardware(self) -> dict[str, Any]:
        from app.services.hardware_diagnostics import hardware_diagnostics
        hw = hardware_diagnostics.get_diagnostics()
        return {
            "platform": hw.os_name + " " + hw.os_version,
            "processor": hw.processor_name,
            "architecture": hw.system_architecture,
            "python_version": platform.python_version(),
            "cpu_cores": f"{hw.cpu_cores_logical} Logical Cores" if hw.cpu_cores_logical else "Available",
            "gpu": ", ".join(hw.gpus) if hw.gpus else "Not detected",
            "npu": f"Detected: {hw.npu_device_name}" if hw.npu_detected else "Not detected",
        }

    def load_model(self, model_key: str) -> dict[str, Any]:
        if model_key == "vision":
            from app.ai.vision.inference_engine import inference_engine
            inference_engine.ensure_loaded()
            return {
                "status": "LOADED",
                "model": "vision",
                "message": "YOLO-X vision model successfully loaded into memory.",
                "details": inference_engine.get_pipeline_status(),
            }
        if model_key == "ocr":
            from app.ai.ocr.ocr_engine import ocr_engine
            ocr_engine.ensure_loaded()
            return {
                "status": "LOADED",
                "model": "ocr",
                "message": "EasyOCR model successfully loaded into memory.",
                "details": ocr_engine.get_status().model_dump(),
            }
        if model_key not in self._models:
            return {"status": "ERROR", "message": f"Unknown model identifier '{model_key}'."}
        return {
            "status": "MODEL_NOT_CONNECTED",
            "model": model_key,
            "message": f"{self._models[model_key].name} integration is scheduled for later phase. No weights loaded.",
        }

    def unload_model(self, model_key: str) -> dict[str, Any]:
        if model_key == "vision":
            from app.ai.vision.inference_engine import inference_engine
            inference_engine.unload()
            return {
                "status": "UNLOADED",
                "model": "vision",
                "message": "YOLO-X vision model successfully unloaded from memory.",
                "details": inference_engine.get_pipeline_status(),
            }
        if model_key == "ocr":
            from app.ai.ocr.ocr_engine import ocr_engine
            ocr_engine.unload()
            return {
                "status": "UNLOADED",
                "model": "ocr",
                "message": "EasyOCR model successfully unloaded from memory.",
                "details": ocr_engine.get_status().model_dump(),
            }
        if model_key not in self._models:
            return {"status": "ERROR", "message": f"Unknown model identifier '{model_key}'."}
        return {
            "status": "UNLOADED",
            "model": model_key,
            "message": f"{self._models[model_key].name} is not loaded.",
        }
