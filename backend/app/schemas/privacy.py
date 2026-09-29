from __future__ import annotations

from pydantic import BaseModel, Field


class PrivacyPolicy(BaseModel):
    camera_enabled: bool = Field(default=False, description="User preference: camera access within SENTINEL")
    microphone_enabled: bool = Field(default=False, description="User preference: microphone access within SENTINEL")
    memory_enabled: bool = Field(default=True, description="Whether persistent memory saving is active")
    local_ai_mode: str = Field(default="local_only", description="Preferred AI mode: local_only, hybrid, disabled")
    cloud_enabled: bool = Field(default=False, description="Cloud AI services - default disabled for privacy")
    retention_days: int = Field(default=0, description="0 = indefinite local retention until user deletion")
    telemetry_enabled: bool = Field(default=False, description="No telemetry or surveillance")

    model_config = {"from_attributes": True}


class PrivacyPolicyUpdate(BaseModel):
    camera_enabled: bool | None = None
    microphone_enabled: bool | None = None
    memory_enabled: bool | None = None
    local_ai_mode: str | None = None
    cloud_enabled: bool | None = None
    retention_days: int | None = None
    telemetry_enabled: bool | None = None
