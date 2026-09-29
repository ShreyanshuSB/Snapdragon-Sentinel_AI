from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
import numpy as np


class BaseSpeechAdapter(ABC):
    """
    Abstract base interface for speech recognition adapters.
    Ensures seamless interchange between local CPU development models,
    mock test adapters, and target Qualcomm Snapdragon NPU runtimes.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the model/adapter."""
        ...

    @property
    @abstractmethod
    def device(self) -> str:
        """Execution device, e.g. 'Intel CPU (Host)' or 'Snapdragon Hexagon NPU'."""
        ...

    @property
    @abstractmethod
    def runtime(self) -> str:
        """Runtime name, e.g. 'PyTorch CPU' or 'QNNExecutionProvider'."""
        ...

    @property
    @abstractmethod
    def is_verified(self) -> bool:
        """Truthful verification status."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether the adapter is initialized and ready on current host."""
        ...

    @abstractmethod
    def transcribe(
        self,
        audio_16k: np.ndarray,
        language: str | None = None,
    ) -> tuple[str, str | None, float | None, float]:
        """
        Transcribe 16kHz mono float32 audio.

        Returns:
            tuple of (text, language_detected, confidence_or_none, inference_latency_ms)
        """
        ...

    @abstractmethod
    def get_metadata(self) -> dict[str, Any]:
        """Return structured model and runtime metadata."""
        ...

    def load(self) -> bool:
        """Explicitly load model weights into host memory."""
        return True

    def unload(self) -> None:
        """Unload model weights to release memory."""
        pass

