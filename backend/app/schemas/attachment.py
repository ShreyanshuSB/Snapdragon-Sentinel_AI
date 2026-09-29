from __future__ import annotations

import datetime as dt
from pydantic import BaseModel, Field


class AttachmentRead(BaseModel):
    id: int
    file_id: str
    file_name: str
    file_path: str
    file_size: int
    mime_type: str | None = None
    sha256: str | None = None
    memory_id: int | None = None
    conversation_id: int | None = None
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class AttachmentUploadResponse(BaseModel):
    status: str = "STORED_LOCALLY"
    file_id: str
    file_name: str
    file_path: str
    file_size: int
    mime_type: str
    sha256: str
    attachment_id: int | None = None
    message: str = "File securely validated and saved locally."
