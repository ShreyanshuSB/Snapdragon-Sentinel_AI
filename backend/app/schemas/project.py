from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectRead(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime
    memory_count: int = 0
