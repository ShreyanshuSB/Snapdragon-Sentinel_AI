from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.chat import (
    ContextUsedSummary,
    SourceAttribution,
    VerificationInfo,
)


class GroundingActionType(str, Enum):
    HIGHLIGHT_OBJECT = "HIGHLIGHT_OBJECT"
    OPEN_VISION = "OPEN_VISION"
    OPEN_DOCUMENT = "OPEN_DOCUMENT"
    OPEN_MEMORY = "OPEN_MEMORY"
    OPEN_SOURCE = "OPEN_SOURCE"
    NONE = "NONE"


class GroundingAction(BaseModel):
    action: GroundingActionType = Field(default=GroundingActionType.NONE, description="Structured UI action")
    target_id: str | int | None = Field(default=None, description="Identifier of target object/doc/memory")
    label: str | None = Field(default=None, description="Human-readable label of target item")
    box_2d: dict[str, Any] | list[float] | None = Field(default=None, description="Bounding box if targeting visual object")
    zone: str | None = Field(default=None, description="Spatial zone (e.g. CENTER, TOP_LEFT)")
    document_id: str | None = Field(default=None, description="Referenced document ID")
    page: int | None = Field(default=None, description="Referenced page number")
    memory_id: int | None = Field(default=None, description="Referenced memory ID")
    confidence: float | None = Field(default=None, description="Action/match confidence")
    description: str | None = Field(default=None, description="Human explanation of action")


class EvidenceCategory(str, Enum):
    OBSERVED = "OBSERVED"
    RETRIEVED = "RETRIEVED"
    INFERRED = "INFERRED"
    CONVERSATION = "CONVERSATION"


class EvidenceItem(BaseModel):
    category: EvidenceCategory = Field(..., description="Epistemic status: OBSERVED, RETRIEVED, INFERRED")
    source_type: str = Field(..., description="VISION, OCR, MEMORY, DOCUMENT, WORKSPACE_TRACK, CONVERSATION")
    source_id: str | int = Field(..., description="Stable ID of evidence source")
    title: str = Field(..., description="Label or title")
    snippet: str = Field(..., description="Relevant extracted evidence snippet")
    score: float | None = Field(default=None, description="Confidence or similarity score")
    page: int | None = Field(default=None, description="Page number for document evidence")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context metadata")


class OrchestratorTiming(BaseModel):
    input_normalization_ms: float = Field(default=0.0, description="Input validation & shaping latency")
    evidence_collection_ms: float = Field(default=0.0, description="Vision/OCR/Memory evidence query latency")
    retrieval_ms: float = Field(default=0.0, description="Vector/hybrid search latency")
    context_build_ms: float = Field(default=0.0, description="Context hierarchy budgeting latency")
    image_prepare_ms: float = Field(default=0.0, description="Image tensor/bbox preparation latency")
    generation_ms: float = Field(default=0.0, description="Reasoning model inference latency")
    validation_ms: float = Field(default=0.0, description="Response validation and citation safety check latency")
    action_generation_ms: float = Field(default=0.0, description="Structured UI grounding action resolution latency")
    total_ms: float = Field(default=0.0, description="Total pipeline latency")
    model_inference_status: str = Field(default="READY", description="Truthful model execution status")


class MultimodalQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User question or query text")
    source: str = Field(default="text", description="Input modality: text, voice, vision, document")
    conversation_id: int | None = Field(default=None, description="Optional conversation session ID")
    project_id: int | None = Field(default=None, description="Optional project filter")
    image_id: str | None = Field(default=None, description="Uploaded image file ID")
    image_context: str | None = Field(default=None, description="Base64 encoded frame or image data")
    document_id: str | None = Field(default=None, description="Directly attached document ID")
    page_number: int | None = Field(default=None, description="Directly attached document page")
    memory_id: int | None = Field(default=None, description="Directly attached memory ID")
    voice_transcript: str | None = Field(default=None, description="Original STT transcript if voice input")
    voice_metadata: dict[str, Any] | None = Field(default=None, description="Voice STT duration/confidence metadata")
    workspace_state: dict[str, Any] | None = Field(default=None, description="Optional desk/workspace track state snapshot")
    mode: str = Field(default="live", description="Execution mode: 'live' or 'demo'")


class MultimodalQueryResponse(BaseModel):
    query: str = Field(..., description="Processed user query")
    answer: str = Field(..., description="Grounded, validated answer")
    status: str = Field(default="SUCCESS", description="Execution status")
    mode: str = Field(default="LIVE", description="LIVE or DEMO / SIMULATION")
    sources: list[SourceAttribution] = Field(default_factory=list, description="Validated source citations")
    citations: list[str] = Field(default_factory=list, description="Human-readable citation strings")
    evidence: list[EvidenceItem] = Field(default_factory=list, description="Structured evidence items used")
    action: GroundingAction = Field(default_factory=GroundingAction, description="Structured UI visual action")
    observed_facts: list[str] = Field(default_factory=list, description="Facts directly detected via vision/OCR")
    retrieved_facts: list[str] = Field(default_factory=list, description="Facts retrieved from user memory/docs")
    inferred_facts: list[str] = Field(default_factory=list, description="Logical/spatial deductions made")
    uncertainties: list[str] = Field(default_factory=list, description="Missing or ambiguous aspects acknowledged")
    context_summary: ContextUsedSummary = Field(default_factory=ContextUsedSummary)
    timing: OrchestratorTiming = Field(default_factory=OrchestratorTiming)
    verification: VerificationInfo = Field(default_factory=VerificationInfo)
    conversation_id: int | None = Field(default=None)
    user_message_id: int | None = Field(default=None)
    assistant_message_id: int | None = Field(default=None)

    model_config = ConfigDict(from_attributes=True)
