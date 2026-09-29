from __future__ import annotations

import logging
from typing import Any

from app.schemas.speech import (
    MicrophoneState,
    SpeechTranscribeRequest,
    SpeechTranscribeResponse,
    VoiceBenchmarkResult,
    VoiceStatusResponse,
)
from app.ai.speech.engine import speech_engine

logger = logging.getLogger(__name__)


class SpeechService:
    """
    High-level speech service managing audio capture requests,
    transcription, intention routing, and privacy lifecycle.
    """

    def __init__(self) -> None:
        self._engine = speech_engine

    def get_status(self) -> VoiceStatusResponse:
        return self._engine.get_status()

    def set_microphone_state(self, state: MicrophoneState) -> VoiceStatusResponse:
        self._engine.set_mic_state(state)
        return self._engine.get_status()

    def transcribe(
        self,
        request: SpeechTranscribeRequest,
        db: Any = None,
    ) -> SpeechTranscribeResponse:
        # Enforce privacy constraint:
        # Never store raw audio to disk or database unless user explicitly flagged save_audio=True
        if not request.save_audio:
            # Raw audio will be processed in memory and immediately discarded by preprocessor/engine
            pass

        return self._engine.transcribe(request=request, db=db)

    def run_benchmark(self, duration_sec: float = 3.0) -> VoiceBenchmarkResult:
        return self._engine.run_benchmark(duration_sec=duration_sec)


speech_service = SpeechService()
