from __future__ import annotations

import datetime as dt
from typing import Any
from pydantic import BaseModel, Field
from app.schemas.ocr import TextRegion


class DocumentPageResponse(BaseModel):
    page_number: int
    width: float = 0.0
    height: float = 0.0
    text: str = ""
    has_ocr: bool = False
    regions: list[TextRegion] = Field(default_factory=list)
    processing_time_ms: float = 0.0


class DocumentResponse(BaseModel):
    document_id: str
    file_id: str
    file_name: str
    file_size: int
    mime_type: str
    source_type: str
    status: str
    page_count: int
    ocr_pages_count: int
    extracted_text: str
    extraction_method: str
    processing_time_ms: float
    created_at: dt.datetime
    updated_at: dt.datetime
    pages: list[DocumentPageResponse] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentCreateRequest(BaseModel):
    file_id: str = Field(..., description="ID of uploaded file attachment")
    force_ocr: bool = Field(default=False, description="Force OCR even if PDF contains native text")


class DocumentSearchHit(BaseModel):
    document_id: str
    file_id: str
    file_name: str
    page_number: int | None
    source_type: str
    snippet: str
    match_count: int = 1
    created_at: dt.datetime


class DocumentSearchResponse(BaseModel):
    query: str
    total_hits: int
    results: list[DocumentSearchHit] = Field(default_factory=list)
