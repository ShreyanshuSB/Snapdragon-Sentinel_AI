from __future__ import annotations

from typing import Any

from app.ai.interfaces import EmbeddingEngine, MemoryRetriever, OCRService, ReasoningEngine, SpeechEngine, VisionEngine


class PlaceholderVisionEngine(VisionEngine):
    def analyze(self, image_path: str | None = None, prompt: str | None = None) -> dict[str, Any]:
        return {"status": "MODEL_NOT_CONNECTED", "message": "Vision model not connected.", "objects": [], "ocr": []}

    def status(self) -> str:
        return "MODEL_NOT_CONNECTED"


class PlaceholderOCRService(OCRService):
    def extract_text(self, image_path: str | None = None, text: str | None = None) -> dict[str, Any]:
        return {"status": "MODEL_NOT_CONNECTED", "message": "OCR model not connected.", "text": ""}

    def status(self) -> str:
        return "MODEL_NOT_CONNECTED"


class PlaceholderSpeechEngine(SpeechEngine):
    def transcribe(self, audio_path: str | None = None) -> dict[str, Any]:
        return {"status": "MODEL_NOT_CONNECTED", "message": "Speech model not connected.", "transcript": ""}

    def status(self) -> str:
        return "MODEL_NOT_CONNECTED"


class PlaceholderReasoningEngine(ReasoningEngine):
    def generate(self, prompt: str, context: list[str] | None = None) -> dict[str, Any]:
        return {"status": "MODEL_NOT_CONNECTED", "message": "Local AI model is not connected yet.", "response": "Local AI model is not connected yet."}

    def status(self) -> str:
        return "MODEL_NOT_CONNECTED"


class PlaceholderEmbeddingEngine(EmbeddingEngine):
    def embed(self, text: str) -> list[float]:
        return []

    def status(self) -> str:
        return "MODEL_NOT_CONNECTED"


class PlaceholderMemoryRetriever(MemoryRetriever):
    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return []

    def status(self) -> str:
        return "MODEL_NOT_CONNECTED"
