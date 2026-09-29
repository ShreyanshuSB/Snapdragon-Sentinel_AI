from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class MicrophoneState(str, Enum):
    IDLE = "IDLE"
    REQUESTING_PERMISSION = "REQUESTING_PERMISSION"
    READY = "READY"
    RECORDING = "RECORDING"
    PROCESSING = "PROCESSING"
    TRANSCRIBED = "TRANSCRIBED"
    ERROR = "ERROR"


class VoiceIntentType(str, Enum):
    FIND_IT = "FIND_IT"
    REMEMBER_OBJECT = "REMEMBER_OBJECT"
    SEARCH_MEMORY = "SEARCH_MEMORY"
    SEARCH_DOCUMENTS = "SEARCH_DOCUMENTS"
    ASK_SENTINEL = "ASK_SENTINEL"
    GENERAL_QUERY = "GENERAL_QUERY"
    UNKNOWN = "UNKNOWN"


class VoiceActionResult(BaseModel):
    intent: VoiceIntentType = Field(..., description="Classified intent from transcript")
    summary: str = Field(..., description="Spoken or textual summary of the action taken")
    raw_query: str = Field(default="", description="Extracted target query or statement")
    grounded_target_id: str | None = Field(default=None, description="Visual track ID if object was found")
    grounded_target_name: str | None = Field(default=None, description="Object class or label")
    grounded_region: str | None = Field(default=None, description="Spatial region in workspace")
    grounded_confidence: float | None = Field(default=None, description="Spatial or detection confidence")
    grounded_relations: list[str] = Field(default_factory=list, description="Spatial relations e.g. 'right_of keyboard'")
    grounding_action: dict[str, Any] | None = Field(default=None, description="Structured UI grounding action")
    action_data: dict[str, Any] = Field(default_factory=dict, description="Structured payload from routed service")


class SpeechTranscribeRequest(BaseModel):
    audio_base64: str | None = Field(default=None, description="Base64 encoded audio payload (WAV or raw PCM)")
    audio_format: str = Field(default="wav", description="Audio container format: wav, pcm, webm")
    sample_rate: int = Field(default=16000, description="Sampling rate in Hz (default 16000)")
    language: str | None = Field(default=None, description="Optional ISO language code, e.g. 'en'")
    project_id: str = Field(default="default", description="Active project context")
    route_intent: bool = Field(default=True, description="Whether to route transcript into SENTINEL action engine")
    save_audio: bool = Field(
        default=False,
        description="Privacy constraint: Audio is discarded after processing unless explicitly requested",
    )


class SpeechTranscribeResponse(BaseModel):
    text: str = Field(..., description="Recognized transcript")
    language: str | None = Field(default="en", description="Detected or specified language")
    confidence: float | None = Field(
        default=None,
        description="Confidence score if exposed by runtime; None if uncalibrated",
    )
    duration_ms: float = Field(..., description="Total pipeline latency in milliseconds")
    audio_duration_seconds: float = Field(..., description="Length of input audio in seconds")
    real_time_factor: float | None = Field(
        default=None,
        description="Real-Time Factor (RTF = inference_seconds / audio_seconds)",
    )
    model: str = Field(..., description="Name of the speech model used")
    runtime: str = Field(..., description="Active execution runtime/provider")
    status: str = Field(default="success", description="Status string: success, empty, error")
    action_result: VoiceActionResult | None = Field(
        default=None,
        description="Grounded SENTINEL action result if intent routing was requested",
    )


class VoiceStatusResponse(BaseModel):
    microphone_state: MicrophoneState = Field(default=MicrophoneState.IDLE)
    model_name: str
    model_family: str
    active_runtime: str
    host_hardware: str
    host_available: bool
    snapdragon_target: str
    snapdragon_verification_status: str = "NOT VERIFIED"
    privacy_policy: str = "Local processing only. Raw audio discarded immediately after transcription."
    max_recording_seconds: float = 30.0


class VoiceBenchmarkResult(BaseModel):
    model_name: str
    device: str
    runtime: str
    audio_duration_seconds: float
    load_latency_ms: float
    preprocessing_latency_ms: float
    inference_latency_ms: float
    total_latency_ms: float
    real_time_factor: float
    snapdragon_status: str = "NOT VERIFIED"
