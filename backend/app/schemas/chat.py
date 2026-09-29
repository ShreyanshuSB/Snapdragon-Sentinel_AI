from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SourceAttribution(BaseModel):
    type: str = Field(..., description="Source type: MEMORY, DOCUMENT, OCR, VISION")
    id: str | int = Field(..., description="Stable source identifier")
    title: str = Field(..., description="Human-readable title or label")
    page: int | None = Field(default=None, description="Page number for documents")
    chunk_index: int | None = Field(default=None, description="Chunk index if applicable")
    snippet: str | None = Field(default=None, description="Text snippet or evidence summary")
    score: float | None = Field(default=None, description="Relevance or confidence score")


class ContextUsedSummary(BaseModel):
    vision_count: int = Field(default=0, description="Number of visual detections included")
    ocr_count: int = Field(default=0, description="Number of OCR regions included")
    memory_count: int = Field(default=0, description="Number of memories retrieved")
    document_count: int = Field(default=0, description="Number of document chunks retrieved")
    project_name: str | None = Field(default=None, description="Active project filter applied")
    total_items: int = Field(default=0, description="Total evidence items in context")


class TimingMetrics(BaseModel):
    retrieval_ms: float = Field(default=0.0, description="Time spent searching memories/docs")
    context_build_ms: float = Field(default=0.0, description="Time spent structuring context")
    image_prepare_ms: float = Field(default=0.0, description="Time spent preparing visual inputs")
    generation_ms: float = Field(default=0.0, description="Model generation time")
    total_ms: float = Field(default=0.0, description="Total request latency")


class VerificationInfo(BaseModel):
    current_device: str = Field(default="Host CPU (Intel)", description="Active host device")
    target_device: str = Field(default="Snapdragon X-series / Hexagon NPU", description="Snapdragon target device")
    npu_verified: bool = Field(default=False, description="Strict NPU execution verification")
    status: str = Field(default="NOT VERIFIED", description="Truthful verification status")


class ChatMessageRequest(BaseModel):
    conversation_id: int | None = None
    text: str = Field(..., min_length=1, description="User question or input")
    project_id: int | None = Field(default=None, description="Project context scope")
    image_id: str | None = Field(default=None, description="File ID or path of attached workspace image")
    image_context: str | None = Field(default=None, description="Base64 or path to attached camera frame")
    document_id: str | None = Field(default=None, description="Attached document ID")
    page_number: int | None = Field(default=None, description="Attached document page")
    memory_id: int | None = Field(default=None, description="Directly attached memory ID")
    context: list[str] = Field(default_factory=list, description="Explicit workspace / document context strings")
    memory_context: list[str] = Field(default_factory=list, description="Memory titles or snippets used")
    model: str | None = Field(default=None, description="Requested model identifier")
    mode: str = Field(default="live", description="Execution mode: 'live' or 'demo'")


class ChatMessageRead(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationCreate(BaseModel):
    title: str = Field(default="New Workspace Chat", max_length=255)


class ConversationRead(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ChatResponse(BaseModel):
    conversation_id: int
    user_message_id: int
    assistant_message_id: int | None = None
    response: str
    answer: str = Field(default="")
    status: str
    mode: str = Field(default="LIVE", description="Execution mode: LIVE or DEMO / SIMULATION")
    action: dict[str, Any] | None = Field(default=None, description="Structured UI grounding action")
    sources: list[SourceAttribution] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    context_used: ContextUsedSummary = Field(default_factory=ContextUsedSummary)
    model: str
    runtime: str = Field(default="CPUExecutionProvider")
    timing: TimingMetrics = Field(default_factory=TimingMetrics)
    verification: VerificationInfo = Field(default_factory=VerificationInfo)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.answer and self.response:
            self.answer = self.response
        elif not self.response and self.answer:
            self.response = self.answer

