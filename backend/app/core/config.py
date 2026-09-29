from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SENTINEL"
    app_tagline: str = "Your private AI that sees, understands, and remembers."
    app_phase: str = "Phase 1 — Foundation"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    
    # Storage
    database_url: str = "sqlite:///./sentinel.db"
    upload_dir: str = "./data/uploads"
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB limit
    allowed_image_types: list[str] = ["image/png", "image/jpeg", "image/jpg", "image/webp"]
    allowed_doc_types: list[str] = ["application/pdf", "text/plain"]

    # Submission & Hardware Target Configuration
    target_profile: str = "snapdragon_x_elite"
    runtime_provider: str = "CPUExecutionProvider"
    host_platform: str = "Intel x86_64"
    npu_verified: bool = False

    # AI Model Selection
    vision_model: str = "yolox_tiny.onnx"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    speech_model: str = "openai/whisper-tiny"
    reasoning_model_target: str = "Qwen/Qwen2.5-VL-3B-Instruct"

    # Runtime Modes
    debug_mode: bool = False
    benchmark_mode: bool = False
    demo_mode: bool = False

    # Privacy Defaults & Hardware Toggles
    camera_enabled: bool = False
    microphone_enabled: bool = False
    memory_enabled: bool = True
    local_ai_mode: str = "local_only"
    cloud_fallback: bool = False

    # Strict Privacy Guarantees
    privacy_strict: bool = True
    no_cloud_guarantee: bool = True
    allow_raw_audio_persistence: bool = False
    allow_raw_video_persistence: bool = False

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()

# Ensure directories exist
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
