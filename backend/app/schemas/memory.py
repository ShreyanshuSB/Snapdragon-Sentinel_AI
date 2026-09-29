from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MemoryBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Memory title")
    content: str = Field(..., min_length=1, description="Memory content/notes")
    summary: str | None = Field(None, description="Optional brief summary")
    category: str = Field(default="note", description="Category: note, project, document, object, conversation")
    source_type: str = Field(default="USER_NOTE", description="Source: USER_NOTE, DOCUMENT, OCR, IMAGE, CONVERSATION, PROJECT, VISION")
    source_id: str | None = Field(None, description="Identifier of the origin document, file, or conversation")
    importance: int = Field(default=1, ge=1, le=5, description="Memory priority / importance level (1-5)")
    metadata: dict[str, Any] = Field(default_factory=dict)
    attachment_path: str | None = None
    project_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class MemoryCreate(MemoryBase):
    pass


class MemoryUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    content: str | None = Field(None, min_length=1)
    summary: str | None = None
    category: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    importance: int | None = Field(None, ge=1, le=5)
    metadata: dict[str, Any] | None = None
    attachment_path: str | None = None
    project_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class MemoryRead(MemoryBase):
    id: int
    embedding_status: str = "PENDING"
    embedding_model: str | None = None
    embedding_dimension: int | None = None
    created_at: datetime
    updated_at: datetime
    project_name: str | None = None


class MemoryListResponse(BaseModel):
    items: list[MemoryRead]
    total: int
    categories: list[str]


class MemoryStats(BaseModel):
    total_memories: int
    category_counts: dict[str, int]
    project_count: int
    ready_embeddings_count: int = 0
    stale_embeddings_count: int = 0
    storage_type: str = "SQLite Local"


class RetrievalResult(BaseModel):
    id: str = Field(..., description="Unique hit ID, e.g. memory-12 or doc-4-chunk-1")
    result_type: str = Field(..., description="MEMORY, DOCUMENT, or OCR")
    title: str = Field(..., description="Display title of the memory or document")
    content: str = Field(..., description="Matched text snippet or memory content")
    score: float = Field(..., description="Combined normalized relevance score [0.0 - 1.0]")
    semantic_score: float = Field(default=0.0, description="Cosine semantic similarity [0.0 - 1.0]")
    keyword_score: float = Field(default=0.0, description="Normalized keyword overlap score [0.0 - 1.0]")
    metadata_score: float = Field(default=0.0, description="Metadata / recency / project match score")
    source_type: str = Field(..., description="USER_NOTE, DOCUMENT, OCR, CONVERSATION, etc.")
    source_id: str | None = None
    project_id: int | None = None
    project_name: str | None = None
    page_number: int | None = None
    chunk_index: int | None = None
    why_matched: str = Field(..., description="Human-explainable reasoning for why this result matched")
    created_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemorySearchQuery(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search question or keyword query")
    search_mode: str = Field(default="HYBRID", description="SEMANTIC, KEYWORD, or HYBRID")
    top_k: int = Field(default=5, ge=1, le=50)
    project_id: int | None = None
    category: str | None = None
    source_type: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    include_documents: bool = Field(default=True, description="Whether to include searchable document chunks")
    w_semantic: float = Field(default=0.65, ge=0.0, le=1.0)
    w_keyword: float = Field(default=0.25, ge=0.0, le=1.0)
    w_metadata: float = Field(default=0.10, ge=0.0, le=1.0)


class MemorySearchResponse(BaseModel):
    query: str
    search_mode: str
    total_results: int
    results: list[RetrievalResult]
    query_embed_ms: float = 0.0
    search_latency_ms: float = 0.0
    total_ms: float = 0.0


class MemoryEmbedRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text string to compute embedding for")


class MemoryEmbedResponse(BaseModel):
    dimension: int
    latency_ms: float
    model_name: str
    model_version: str
    runtime: str
    execution_provider: str
    npu_verified: bool
    status: str = "READY"


class DuplicateCheckRequest(BaseModel):
    title: str
    content: str
    project_id: int | None = None
    threshold: float = Field(default=0.85, ge=0.5, le=1.0)


class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool
    similarity: float
    existing_memory_id: int | None = None
    existing_title: str | None = None
    message: str


class EmbeddingModelMetadata(BaseModel):
    name: str
    version: str
    source: str
    license: str
    dimension: int
    max_sequence_length: int
    runtime: str
    execution_provider: str
    npu_verified: bool
    hardware_target: str
    model_size_mb: float | None = None
    parameters_m: float | None = None
    qualcomm_ai_hub_target: str | None = None
    notes: str | None = None


class EmbeddingStatusResponse(BaseModel):
    state: str
    is_available: bool
    is_loaded: bool
    model: EmbeddingModelMetadata
    ready_memories_count: int
    stale_memories_count: int
    failed_memories_count: int
    reindex_required: bool
    device_label: str
    last_query_embed_ms: float | None = None
    target_model_name: str | None = "nomic-embed-text-v1.5"
    target_device: str | None = "Snapdragon X Elite NPU (Hexagon)"
    npu_status: str | None = "NOT VERIFIED"


class ReindexResponse(BaseModel):
    status: str
    memories_indexed: int
    chunks_indexed: int
    duration_ms: float
    message: str
