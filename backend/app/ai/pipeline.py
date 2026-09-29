from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class ModelLifecycleState(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"
    AVAILABLE = "AVAILABLE"
    LOADING = "LOADING"
    READY = "READY"
    RUNNING = "RUNNING"
    ERROR = "ERROR"


class RuntimeAdapter(ABC):
    """
    Abstract interface for executing inference through an AI execution provider
    (e.g., ONNX Runtime with QNNExecutionProvider or CPUExecutionProvider).
    """

    @abstractmethod
    def initialize(self, model_path: str, provider: str, provider_options: dict[str, Any] | None = None) -> None:
        """Initializes the runtime session with the given provider."""
        raise NotImplementedError

    @abstractmethod
    def run_inference(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Runs forward inference graph pass and returns raw tensor outputs."""
        raise NotImplementedError

    @abstractmethod
    def get_active_provider(self) -> str:
        """Returns the currently active execution provider."""
        raise NotImplementedError

    @abstractmethod
    def is_npu_verified(self) -> bool:
        """Returns whether NPU execution has been genuinely verified on this device."""
        raise NotImplementedError


class VisionModelAdapter(ABC):
    """
    Abstract interface for a specific vision model architecture (e.g., YOLO-X).
    Handles model-specific input preprocessing (resizing, letterbox, normalization)
    and output postprocessing (tensor parsing, confidence thresholding, NMS).
    """

    @abstractmethod
    def preprocess(self, image_data: bytes | Any) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Prepares raw image bytes into model tensor format.
        Returns (model_inputs, transform_metadata).
        """
        raise NotImplementedError

    @abstractmethod
    def postprocess(self, raw_outputs: dict[str, Any], metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Converts model output tensors into normalized bounding boxes and classifications.
        """
        raise NotImplementedError

    @abstractmethod
    def get_model_metadata(self) -> dict[str, Any]:
        """Returns model identifier, task, shape, and parameter metadata."""
        raise NotImplementedError


class InferenceEngine(ABC):
    """
    Coordinates model adapters and runtime adapters to execute an end-to-end inference request.
    Shields higher-level services from tensor details and hardware execution specifics.
    """

    @abstractmethod
    def detect_objects(self, image_bytes: bytes) -> dict[str, Any]:
        """Runs object detection pipeline on raw image bytes."""
        raise NotImplementedError

    @abstractmethod
    def get_pipeline_status(self) -> dict[str, Any]:
        """Returns status of runtime, adapter, provider, and verification."""
        raise NotImplementedError
