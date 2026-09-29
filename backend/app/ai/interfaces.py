from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ModelStatusResult:
    def __init__(self, name: str, available: bool, status: str = "MODEL_NOT_CONNECTED", runtime: str | None = None, version: str | None = None) -> None:
        self.name = name
        self.available = available
        self.status = status
        self.runtime = runtime
        self.version = version


class VisionEngine(ABC):
    @abstractmethod
    def analyze(self, image_path: str | None = None, prompt: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> str:
        raise NotImplementedError


class OCRService(ABC):
    @abstractmethod
    def extract_text(self, image_path: str | None = None, text: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> str:
        raise NotImplementedError


class SpeechEngine(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> str:
        raise NotImplementedError


class ReasoningEngine(ABC):
    @abstractmethod
    def generate(self, prompt: str, context: list[str] | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> str:
        raise NotImplementedError


class EmbeddingEngine(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> str:
        raise NotImplementedError


class MemoryRetriever(ABC):
    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> str:
        raise NotImplementedError
