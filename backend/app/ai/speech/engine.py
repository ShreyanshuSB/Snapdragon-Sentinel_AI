from __future__ import annotations

import logging
import time
from typing import Any
import numpy as np

from app.schemas.speech import (
    MicrophoneState,
    SpeechTranscribeRequest,
    SpeechTranscribeResponse,
    VoiceBenchmarkResult,
    VoiceStatusResponse,
)
from app.ai.speech.adapter import (
    BaseSpeechAdapter,
    MockSpeechAdapter,
    SnapdragonWhisperAdapter,
    WhisperTransformersAdapter,
)
from app.ai.speech.audio_preprocessor import (
    AudioPreprocessingError,
    audio_preprocessor,
)
from app.ai.speech.router import voice_router

logger = logging.getLogger(__name__)


class SpeechEngine:
    """
    Core speech engine orchestrating audio preprocessing, local speech-to-text inference,
    real-time metrics calculation, and action dispatching.
    """

    def __init__(self, adapter: BaseSpeechAdapter | None = None) -> None:
        self._adapter: BaseSpeechAdapter = adapter or WhisperTransformersAdapter()
        self._snapdragon_target_adapter = SnapdragonWhisperAdapter()
        self._mic_state = MicrophoneState.IDLE

    @property
    def adapter(self) -> BaseSpeechAdapter:
        return self._adapter

    def set_adapter(self, adapter: BaseSpeechAdapter) -> None:
        """Allow switching adapter (e.g. for testing with MockSpeechAdapter)."""
        self._adapter = adapter

    def get_status(self) -> VoiceStatusResponse:
        meta = self._adapter.get_metadata()
        return VoiceStatusResponse(
            microphone_state=self._mic_state,
            model_name=meta.get("name", self._adapter.name),
            model_family="Whisper",
            active_runtime=self._adapter.runtime,
            host_hardware=self._adapter.device,
            host_available=self._adapter.is_available,
            snapdragon_target=self._snapdragon_target_adapter.device,
            snapdragon_verification_status="NOT VERIFIED",
            privacy_policy="Local processing only. Raw audio discarded immediately after transcription.",
            max_recording_seconds=audio_preprocessor.MAX_RECORDING_SECONDS,
        )

    def set_mic_state(self, state: MicrophoneState) -> None:
        self._mic_state = state

    def transcribe(
        self,
        request: SpeechTranscribeRequest,
        db: Any = None,
    ) -> SpeechTranscribeResponse:
        t_start = time.perf_counter()
        self._mic_state = MicrophoneState.PROCESSING

        # 1. Check for audio payload
        if not request.audio_base64:
            self._mic_state = MicrophoneState.IDLE
            return SpeechTranscribeResponse(
                text="",
                language=request.language or "en",
                confidence=None,
                duration_ms=0.0,
                audio_duration_seconds=0.0,
                real_time_factor=None,
                model=self._adapter.name,
                runtime=self._adapter.runtime,
                status="empty",
                action_result=None,
            )

        # 2. Preprocess audio
        t_pre = time.perf_counter()
        try:
            audio_arr, duration_sec, is_silence = audio_preprocessor.process(
                audio_input=request.audio_base64,
                audio_format=request.audio_format,
                sample_rate=request.sample_rate,
            )
        except AudioPreprocessingError as e:
            self._mic_state = MicrophoneState.ERROR
            logger.warning("Audio preprocessing error: %s", e)
            total_ms = (time.perf_counter() - t_start) * 1000.0
            return SpeechTranscribeResponse(
                text="",
                language=request.language or "en",
                confidence=None,
                duration_ms=total_ms,
                audio_duration_seconds=0.0,
                real_time_factor=None,
                model=self._adapter.name,
                runtime=self._adapter.runtime,
                status=f"error: {e}",
                action_result=None,
            )

        # 3. Handle silence / empty audio
        if is_silence or len(audio_arr) == 0:
            self._mic_state = MicrophoneState.TRANSCRIBED
            total_ms = (time.perf_counter() - t_start) * 1000.0
            return SpeechTranscribeResponse(
                text="",
                language=request.language or "en",
                confidence=None,
                duration_ms=total_ms,
                audio_duration_seconds=duration_sec,
                real_time_factor=0.0,
                model=self._adapter.name,
                runtime=self._adapter.runtime,
                status="silence",
                action_result=None,
            )

        # 4. Transcribe locally with adapter
        try:
            raw_text, detected_lang, confidence, infer_ms = self._adapter.transcribe(
                audio_16k=audio_arr,
                language=request.language,
            )
        except Exception as e:
            self._mic_state = MicrophoneState.ERROR
            logger.error("Speech transcription error: %s", e)
            total_ms = (time.perf_counter() - t_start) * 1000.0
            return SpeechTranscribeResponse(
                text="",
                language=request.language or "en",
                confidence=None,
                duration_ms=total_ms,
                audio_duration_seconds=duration_sec,
                real_time_factor=None,
                model=self._adapter.name,
                runtime=self._adapter.runtime,
                status=f"error: {e}",
                action_result=None,
            )

        total_ms = (time.perf_counter() - t_start) * 1000.0
        rtf = (infer_ms / 1000.0) / duration_sec if duration_sec > 0 else 0.0

        # Privacy invariant: Ensure raw audio is never retained in memory
        del audio_arr

        # 5. Route intent if requested
        action_result = None
        if request.route_intent and raw_text:
            action_result = voice_router.route(
                transcript=raw_text,
                project_id=request.project_id,
                db=db,
            )

        self._mic_state = MicrophoneState.TRANSCRIBED

        return SpeechTranscribeResponse(
            text=raw_text,
            language=detected_lang or "en",
            confidence=confidence,
            duration_ms=total_ms,
            audio_duration_seconds=duration_sec,
            real_time_factor=round(rtf, 3),
            model=self._adapter.name,
            runtime=self._adapter.runtime,
            status="success",
            action_result=action_result,
        )

    def run_benchmark(self, duration_sec: float = 3.0) -> VoiceBenchmarkResult:
        """
        Run local benchmark measuring real preprocessing and inference latency.
        Strictly labels results with host hardware and reports Snapdragon as NOT VERIFIED.
        """
        sr = 16000
        # Generate synthetic tone with slight noise
        t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
        synthetic_audio = (np.sin(2 * np.pi * 440 * t) * 0.1 + np.random.randn(len(t)) * 0.01).astype(np.float32)

        t_pre0 = time.perf_counter()
        pre_audio, actual_sec, _ = audio_preprocessor.process(
            synthetic_audio,
            audio_format="raw",
            sample_rate=sr,
        )
        pre_ms = (time.perf_counter() - t_pre0) * 1000.0

        t_infer0 = time.perf_counter()
        self._adapter.transcribe(pre_audio, language="en")
        infer_ms = (time.perf_counter() - t_infer0) * 1000.0

        total_ms = pre_ms + infer_ms
        rtf = (infer_ms / 1000.0) / actual_sec if actual_sec > 0 else 0.0

        return VoiceBenchmarkResult(
            model_name=self._adapter.name,
            device=self._adapter.device,
            runtime=self._adapter.runtime,
            audio_duration_seconds=actual_sec,
            load_latency_ms=0.0,
            preprocessing_latency_ms=round(pre_ms, 2),
            inference_latency_ms=round(infer_ms, 2),
            total_latency_ms=round(total_ms, 2),
            real_time_factor=round(rtf, 3),
            snapdragon_status="NOT VERIFIED (Target Configured)",
        )


speech_engine = SpeechEngine()
