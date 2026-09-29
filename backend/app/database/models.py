from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), default="note", index=True)
    source_type: Mapped[str] = mapped_column(String(100), default="USER_NOTE", index=True)
    source_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    importance: Mapped[int] = mapped_column(Integer, default=1)
    attachment_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    # Semantic Vector Fields
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    embedding_status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)  # PENDING, READY, STALE, FAILED
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    embedding_dimension: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[dt.datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    project: Mapped["Project | None"] = relationship("Project", back_populates="memories")
    attachments: Mapped[list["Attachment"]] = relationship("Attachment", back_populates="memory", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[dt.datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    memories: Mapped[list[Memory]] = relationship("Memory", back_populates="project")


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    file_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    memory_id: Mapped[int | None] = mapped_column(ForeignKey("memories.id", ondelete="CASCADE"), nullable=True)
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    mime_type: Mapped[str | None] = mapped_column(String(150), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(default=utc_now)

    memory: Mapped["Memory | None"] = relationship("Memory", back_populates="attachments")
    conversation: Mapped["Conversation | None"] = relationship("Conversation", back_populates="attachments")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="New Workspace Chat")
    created_at: Mapped[dt.datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[dt.datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    messages: Mapped[list["ConversationMessage"]] = relationship(
        "ConversationMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="ConversationMessage.created_at"
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment", back_populates="conversation", cascade="all, delete-orphan"
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(default=utc_now)

    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="messages")


class PrivacySetting(Base):
    __tablename__ = "privacy_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    camera_enabled: Mapped[bool] = mapped_column(default=False)
    microphone_enabled: Mapped[bool] = mapped_column(default=False)
    memory_enabled: Mapped[bool] = mapped_column(default=True)
    local_ai_mode: Mapped[str] = mapped_column(String(50), default="local_only")
    cloud_enabled: Mapped[bool] = mapped_column(default=False)
    retention_days: Mapped[int] = mapped_column(Integer, default=0)
    telemetry_enabled: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[dt.datetime] = mapped_column(default=utc_now, onupdate=utc_now)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    file_id: Mapped[str] = mapped_column(String(64), index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/octet-stream")
    source_type: Mapped[str] = mapped_column(String(50), default="document")  # pdf_text, pdf_scanned, pdf_mixed, image, text_file
    status: Mapped[str] = mapped_column(String(50), default="READY")  # UPLOADED, PROCESSING, READY, PARTIAL, FAILED
    page_count: Mapped[int] = mapped_column(Integer, default=1)
    ocr_pages_count: Mapped[int] = mapped_column(Integer, default=0)
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    extraction_method: Mapped[str] = mapped_column(String(100), default="direct")
    processing_time_ms: Mapped[float] = mapped_column(default=0.0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[dt.datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    pages: Mapped[list["DocumentPage"]] = relationship(
        "DocumentPage", back_populates="document", cascade="all, delete-orphan", order_by="DocumentPage.page_number"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan", order_by="DocumentChunk.chunk_index"
    )


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[float] = mapped_column(default=0.0)
    height: Mapped[float] = mapped_column(default=0.0)
    text: Mapped[str] = mapped_column(Text, default="")
    has_ocr: Mapped[bool] = mapped_column(default=False)
    regions_json: Mapped[list[dict[str, Any]]] = mapped_column("regions", JSON, default=list)
    processing_time_ms: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(default=utc_now)

    document: Mapped[Document] = relationship("Document", back_populates="pages")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    embedding_status: Mapped[str] = mapped_column(String(20), default="READY", index=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    embedding_dimension: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_char: Mapped[int] = mapped_column(Integer, default=0)
    end_char: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(default=utc_now)

    document: Mapped[Document] = relationship("Document", back_populates="chunks")
