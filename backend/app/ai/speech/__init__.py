from __future__ import annotations

from app.ai.speech.adapter import (
    BaseSpeechAdapter,
    MockSpeechAdapter,
    SnapdragonWhisperAdapter,
    WhisperTransformersAdapter,
)
from app.ai.speech.audio_preprocessor import (
    AudioPreprocessingError,
    AudioPreprocessor,
    audio_preprocessor,
)
from app.ai.speech.engine import SpeechEngine, speech_engine
from app.ai.speech.interfaces import BaseSpeechAdapter
from app.ai.speech.router import VoiceActionRouter, voice_router

__all__ = [
    "BaseSpeechAdapter",
    "WhisperTransformersAdapter",
    "SnapdragonWhisperAdapter",
    "MockSpeechAdapter",
    "AudioPreprocessor",
    "audio_preprocessor",
    "AudioPreprocessingError",
    "SpeechEngine",
    "speech_engine",
    "VoiceActionRouter",
    "voice_router",
]
