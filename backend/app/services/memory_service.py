from __future__ import annotations

import logging
from typing import Any
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.ai.memory.embedding_engine import embedding_engine
from app.ai.memory.indexer import indexer
from app.ai.memory.retriever import retriever
from app.database.models import Attachment, Memory, Project
from app.schemas.memory import (
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    EmbeddingStatusResponse,
    MemoryCreate,
    MemoryEmbedRequest,
    MemoryEmbedResponse,
    MemoryRead,
    MemorySearchQuery,
    MemorySearchResponse,
    MemoryStats,
    MemoryUpdate,
    ReindexResponse,
)
from app.services.privacy_service import privacy_service

logger = logging.getLogger(__name__)


class MemoryService:
    def list_memories(
        self,
        db: Session,
        category: str | None = None,
        search: str | None = None,
        project_id: int | None = None,
    ) -> list[MemoryRead]:
        query = db.query(Memory)

        if category and category.lower() != "all":
            query = query.filter(Memory.category == category.lower())

        if project_id is not None:
            query = query.filter(Memory.project_id == project_id)

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Memory.title.ilike(term),
                    Memory.content.ilike(term),
                    Memory.category.ilike(term),
                )
            )

        memories = query.order_by(Memory.created_at.desc()).all()
        return [self._to_read(m) for m in memories]

    def get_memory(self, db: Session, memory_id: int) -> MemoryRead:
        memory = db.query(Memory).filter(Memory.id == memory_id).first()
        if not memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory with ID {memory_id} not found.",
            )
        return self._to_read(memory)

    def create_memory(self, db: Session, payload: MemoryCreate) -> MemoryRead:
        if not privacy_service.is_memory_enabled():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Memory persistence is disabled in Settings. Enable persistent memory to save.",
            )

        # Validate project if provided
        if payload.project_id is not None:
            project = db.query(Project).filter(Project.id == payload.project_id).first()
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Project with ID {payload.project_id} does not exist.",
                )

        db_memory = Memory(
            title=payload.title.strip(),
            content=payload.content.strip(),
            summary=payload.summary.strip() if payload.summary else None,
            category=payload.category.lower(),
            source_type=payload.source_type,
            source_id=payload.source_id,
            importance=payload.importance,
            attachment_path=payload.attachment_path,
            project_id=payload.project_id,
            metadata_json=payload.metadata,
            embedding_status="PENDING",
        )
        db.add(db_memory)
        db.commit()
        db.refresh(db_memory)

        # Automatically generate local embedding
        indexer.index_memory(db, db_memory)

        return self._to_read(db_memory)

    def update_memory(self, db: Session, memory_id: int, payload: MemoryUpdate) -> MemoryRead:
        memory = db.query(Memory).filter(Memory.id == memory_id).first()
        if not memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory with ID {memory_id} not found.",
            )

        content_changed = False
        if payload.title is not None and payload.title != memory.title:
            memory.title = payload.title.strip()
            content_changed = True
        if payload.content is not None and payload.content != memory.content:
            memory.content = payload.content.strip()
            content_changed = True
        if payload.summary is not None:
            memory.summary = payload.summary.strip() if payload.summary else None
            content_changed = True
        if payload.category is not None:
            memory.category = payload.category.lower()
        if payload.source_type is not None:
            memory.source_type = payload.source_type
        if payload.source_id is not None:
            memory.source_id = payload.source_id
        if payload.importance is not None:
            memory.importance = payload.importance
        if payload.attachment_path is not None:
            memory.attachment_path = payload.attachment_path
        if payload.metadata is not None:
            memory.metadata_json = payload.metadata
        if payload.project_id is not None:
            project = db.query(Project).filter(Project.id == payload.project_id).first()
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Project with ID {payload.project_id} does not exist.",
                )
            memory.project_id = payload.project_id

        if content_changed:
            memory.embedding_status = "STALE"
            db.commit()
            db.refresh(memory)
            # Re-generate embedding
            indexer.index_memory(db, memory)
        else:
            db.commit()
            db.refresh(memory)

        return self._to_read(memory)

    def delete_memory(self, db: Session, memory_id: int) -> dict[str, str]:
        memory = db.query(Memory).filter(Memory.id == memory_id).first()
        if not memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory with ID {memory_id} not found.",
            )
        db.delete(memory)
        db.commit()
        return {"status": "success", "message": f"Memory '{memory.title}' deleted successfully."}

    def delete_all_memories(self, db: Session) -> dict[str, Any]:
        count = db.query(Memory).count()
        db.query(Attachment).delete()
        db.query(Memory).delete()
        db.commit()
        return {
            "status": "success",
            "message": f"All {count} memories removed successfully.",
            "deleted_count": count,
        }

    def embed_text(self, req: MemoryEmbedRequest) -> MemoryEmbedResponse:
        """Computes a local vector for the provided text string and returns execution metrics."""
        vec, latency_ms = embedding_engine.embed_text(req.text, is_query=False)
        meta = embedding_engine.get_metadata()
        runtime_adapter = embedding_engine._adapter.get_runtime_adapter()
        return MemoryEmbedResponse(
            dimension=vec.shape[0],
            latency_ms=round(latency_ms, 2),
            model_name=meta.name,
            model_version=meta.version,
            runtime=runtime_adapter.get_runtime_name(),
            execution_provider=runtime_adapter.get_provider_name(),
            npu_verified=runtime_adapter.is_npu_verified(),
            status="READY",
        )

    def check_duplicate(self, db: Session, req: DuplicateCheckRequest) -> DuplicateCheckResponse:
        """
        Calculates lexical and semantic similarity against existing memories.
        Warns user if duplicate is detected without modifying or deleting anything.
        """
        mem_query = select(Memory.id, Memory.title, Memory.content, Memory.embedding)
        if req.project_id is not None:
            mem_query = mem_query.where(Memory.project_id == req.project_id)

        rows = db.execute(mem_query).all()
        existing_items = [(row[0], row[1], row[2], row[3]) for row in rows if row[3] is not None]

        full_candidate = f"{req.title}\n{req.content}"
        is_dup, sim, match_id, match_title = embedding_engine.check_duplicate(
            full_candidate, existing_items, threshold=req.threshold
        )

        msg = "No duplicate detected."
        if is_dup:
            msg = f"Similar memory already exists: '{match_title}' (similarity {sim * 100:.1f}%)."

        return DuplicateCheckResponse(
            is_duplicate=is_dup,
            similarity=sim,
            existing_memory_id=match_id,
            existing_title=match_title,
            message=msg,
        )

    def search_memories(self, db: Session, query: MemorySearchQuery) -> MemorySearchResponse:
        """
        Executes semantic, keyword, or hybrid retrieval across memories and document chunks.
        """
        return retriever.search(db, query)

    def reindex_memories(self, db: Session, force: bool = False, include_documents: bool = True) -> ReindexResponse:
        """
        Idempotently reindexes all memories and optionally document chunks.
        """
        if include_documents:
            m_count, d_count, duration_ms = indexer.reindex_all(db, force=force)
            return ReindexResponse(
                status="SUCCESS",
                memories_indexed=m_count,
                chunks_indexed=d_count,
                duration_ms=round(duration_ms, 2),
                message=f"Reindexed {m_count} memories and {d_count} document chunks in {duration_ms:.1f} ms.",
            )
        else:
            m_count, duration_ms = indexer.reindex_all_memories(db, force=force)
            return ReindexResponse(
                status="SUCCESS",
                memories_indexed=m_count,
                chunks_indexed=0,
                duration_ms=round(duration_ms, 2),
                message=f"Reindexed {m_count} memory vectors in {duration_ms:.1f} ms.",
            )

    def get_embedding_status(self, db: Session) -> EmbeddingStatusResponse:
        ready = db.query(Memory).filter(Memory.embedding_status == "READY").count()
        stale = db.query(Memory).filter(Memory.embedding_status == "STALE").count()
        failed = db.query(Memory).filter(Memory.embedding_status == "FAILED").count()

        meta = embedding_engine.get_metadata()
        mismatched = (
            db.query(Memory)
            .filter(
                Memory.embedding != None,  # noqa: E711
                Memory.embedding_dimension != meta.dimension,
            )
            .count()
        )
        reindex_req = (mismatched > 0) or (stale > 0)

        return embedding_engine.get_status(
            ready_count=ready,
            stale_count=stale,
            failed_count=failed,
            reindex_required=reindex_req,
        )

    def get_stats(self, db: Session) -> MemoryStats:
        total = db.query(Memory).count()
        categories_raw = (
            db.query(Memory.category, func.count(Memory.id))
            .group_by(Memory.category)
            .all()
        )
        cat_dict = {cat: count for cat, count in categories_raw}
        project_count = db.query(Project).count()
        ready = db.query(Memory).filter(Memory.embedding_status == "READY").count()
        stale = db.query(Memory).filter(Memory.embedding_status == "STALE").count()

        return MemoryStats(
            total_memories=total,
            category_counts=cat_dict,
            project_count=project_count,
            ready_embeddings_count=ready,
            stale_embeddings_count=stale,
            storage_type="SQLite Local",
        )

    @staticmethod
    def _to_read(m: Memory) -> MemoryRead:
        return MemoryRead(
            id=m.id,
            title=m.title,
            content=m.content,
            summary=m.summary,
            category=m.category,
            source_type=m.source_type or "USER_NOTE",
            source_id=m.source_id,
            importance=m.importance or 1,
            attachment_path=m.attachment_path,
            project_id=m.project_id,
            project_name=m.project.name if m.project else None,
            metadata=m.metadata_json or {},
            embedding_status=m.embedding_status or "PENDING",
            embedding_model=m.embedding_model,
            embedding_dimension=m.embedding_dimension,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )


memory_service = MemoryService()
