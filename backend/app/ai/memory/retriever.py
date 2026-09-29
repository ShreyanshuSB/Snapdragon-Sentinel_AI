from __future__ import annotations

import datetime as dt
import logging
import re
import time
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.memory.embedding_engine import embedding_engine
from app.database.models import Document, DocumentChunk, Memory
from app.schemas.memory import MemorySearchQuery, MemorySearchResponse, RetrievalResult

logger = logging.getLogger(__name__)


class MemoryRetriever:
    """
    Local hybrid search engine combining:
    1. Semantic similarity (dense cosine similarity on float32 vectors)
    2. Lexical keyword matching (token-overlap and substring scoring)
    3. Metadata filtering (project, category, source_type, date range)

    Scoring formula:
        Score_hybrid = (w_s * S_semantic + w_k * S_keyword + w_m * S_metadata) / (w_s + w_k + w_m)
    where:
        - S_semantic in [0.0, 1.0] from cosine_similarity(query_vec, candidate_vec)
        - S_keyword in [0.0, 1.0] from query token containment ratio and substring matching
        - S_metadata in [0.0, 1.0] from project match, priority/importance weight, and recency
    """

    @staticmethod
    def _compute_keyword_score(query_tokens: set[str], query_str: str, text: str) -> float:
        """
        Computes normalized keyword match score in [0.0, 1.0] based on token containment and exact substring matching.
        """
        if not query_tokens or not text:
            return 0.0

        lowered_text = text.lower()
        matched = 0
        for token in query_tokens:
            if token in lowered_text:
                matched += 1

        ratio = matched / len(query_tokens)

        # Exact phrase bonus (up to +0.2 if full multi-word query is found as exact substring)
        if len(query_tokens) > 1 and query_str.lower() in lowered_text:
            ratio = min(1.0, ratio + 0.2)

        return min(1.0, max(0.0, ratio))

    def search_keyword(self, db: Session, req: MemorySearchQuery) -> MemorySearchResponse:
        """Convenience method for pure keyword retrieval."""
        req_copy = req.model_copy(update={"search_mode": "KEYWORD"})
        return self.search(db, req_copy)

    def search_semantic(self, db: Session, req: MemorySearchQuery) -> MemorySearchResponse:
        """Convenience method for pure semantic retrieval."""
        req_copy = req.model_copy(update={"search_mode": "SEMANTIC"})
        return self.search(db, req_copy)

    def search_hybrid(self, db: Session, req: MemorySearchQuery) -> MemorySearchResponse:
        """Convenience method for hybrid retrieval."""
        req_copy = req.model_copy(update={"search_mode": "HYBRID"})
        return self.search(db, req_copy)

    def search(self, db: Session, req: MemorySearchQuery) -> MemorySearchResponse:
        total_start = time.perf_counter()

        query_str = req.query.strip()
        if not query_str:
            return MemorySearchResponse(
                query=query_str,
                search_mode=req.search_mode,
                total_results=0,
                results=[],
                query_embed_ms=0.0,
                search_latency_ms=0.0,
                total_ms=0.0,
            )

        # 1. Generate query embedding (only needed if mode is SEMANTIC or HYBRID)
        query_vec: np.ndarray | None = None
        query_embed_ms = 0.0

        if req.search_mode.upper() in ("SEMANTIC", "HYBRID"):
            try:
                query_vec, query_embed_ms = embedding_engine.embed_text(query_str, is_query=True)
            except Exception as e:
                logger.warning("Query embedding generation failed, falling back to keyword search: %s", e)
                query_vec = None

        search_start = time.perf_counter()

        # Tokenize query for keyword scoring
        clean_tokens = set(re.findall(r'\b\w+\b', query_str.lower()))

        # Current active model metadata for dimension validation
        active_meta = embedding_engine.get_metadata()
        active_dim = active_meta.dimension

        scored_candidates: list[RetrievalResult] = []

        # Parse date filters if provided
        date_from_dt: dt.datetime | None = None
        date_to_dt: dt.datetime | None = None
        if req.date_from:
            try:
                date_from_dt = dt.datetime.fromisoformat(req.date_from.replace("Z", "+00:00"))
            except Exception:
                pass
        if req.date_to:
            try:
                date_to_dt = dt.datetime.fromisoformat(req.date_to.replace("Z", "+00:00"))
            except Exception:
                pass

        # 2. Search Memories Table
        mem_stmt = select(Memory)
        if req.project_id is not None:
            mem_stmt = mem_stmt.where(Memory.project_id == req.project_id)
        if req.category and req.category.lower() != "all":
            mem_stmt = mem_stmt.where(Memory.category == req.category.lower())
        if req.source_type:
            mem_stmt = mem_stmt.where(Memory.source_type == req.source_type)

        memories = db.execute(mem_stmt).scalars().all()

        for mem in memories:
            # Apply date filters
            if date_from_dt and mem.created_at and mem.created_at < date_from_dt:
                continue
            if date_to_dt and mem.created_at and mem.created_at > date_to_dt:
                continue

            # Semantic score
            sem_score = 0.0
            if (
                query_vec is not None
                and mem.embedding is not None
                and mem.embedding_status == "READY"
                and mem.embedding_dimension == active_dim
            ):
                try:
                    mem_vec = embedding_engine.bytes_to_vector(mem.embedding, expected_dim=active_dim)
                    sem_score = embedding_engine.cosine_similarity(query_vec, mem_vec)
                except Exception:
                    sem_score = 0.0

            # Keyword score over title, content, summary
            full_text = f"{mem.title} {mem.content} {mem.summary or ''}"
            kw_score = self._compute_keyword_score(clean_tokens, query_str, full_text)

            # Metadata score (project match + high priority + recency)
            meta_score = 0.0
            if req.project_id and mem.project_id == req.project_id:
                meta_score += 0.5
            if mem.importance >= 4:
                meta_score += 0.3
            meta_score = min(1.0, meta_score)

            # Mode selection & final score calculation
            mode = req.search_mode.upper()
            if mode == "SEMANTIC":
                final_score = sem_score
            elif mode == "KEYWORD":
                final_score = kw_score
            else:  # HYBRID
                w_s, w_k, w_m = req.w_semantic, req.w_keyword, req.w_metadata
                total_w = max(0.0001, w_s + w_k + w_m)
                final_score = (w_s * sem_score + w_k * kw_score + w_m * meta_score) / total_w

            # Filter out entries with zero relevance
            if final_score < 0.04:
                continue

            why_parts = []
            if sem_score >= 0.45:
                why_parts.append(f"Semantic match ({sem_score:.2f})")
            if kw_score > 0:
                why_parts.append(f"Keyword match ({kw_score * 100:.0f}%)")
            if meta_score > 0:
                why_parts.append("Project/Priority relevance")
            why_text = " • ".join(why_parts) if why_parts else f"Relevance score {final_score:.2f}"

            scored_candidates.append(
                RetrievalResult(
                    id=f"memory-{mem.id}",
                    result_type="MEMORY",
                    title=mem.title,
                    content=mem.content,
                    score=round(final_score, 4),
                    semantic_score=round(sem_score, 4),
                    keyword_score=round(kw_score, 4),
                    metadata_score=round(meta_score, 4),
                    source_type=mem.source_type or "USER_NOTE",
                    source_id=mem.source_id or str(mem.id),
                    project_id=mem.project_id,
                    project_name=mem.project.name if mem.project else None,
                    page_number=None,
                    chunk_index=None,
                    why_matched=why_text,
                    created_at=mem.created_at.isoformat() if mem.created_at else None,
                    metadata=mem.metadata_json or {},
                )
            )

        # 3. Search Document Chunks (Source Material) if requested
        if req.include_documents and (req.source_type is None or req.source_type.upper() in ("DOCUMENT", "PDF")):
            chunk_stmt = select(DocumentChunk, Document).join(
                Document, DocumentChunk.document_id == Document.document_id
            )
            chunks_and_docs = db.execute(chunk_stmt).all()

            for chunk, doc in chunks_and_docs:
                if date_from_dt and chunk.created_at and chunk.created_at < date_from_dt:
                    continue
                if date_to_dt and chunk.created_at and chunk.created_at > date_to_dt:
                    continue

                sem_score = 0.0
                if (
                    query_vec is not None
                    and chunk.embedding is not None
                    and chunk.embedding_dimension == active_dim
                ):
                    try:
                        chunk_vec = embedding_engine.bytes_to_vector(chunk.embedding, expected_dim=active_dim)
                        sem_score = embedding_engine.cosine_similarity(query_vec, chunk_vec)
                    except Exception:
                        sem_score = 0.0

                full_text = f"{doc.file_name} {chunk.text_content}"
                kw_score = self._compute_keyword_score(clean_tokens, query_str, full_text)
                meta_score = 0.0

                mode = req.search_mode.upper()
                if mode == "SEMANTIC":
                    final_score = sem_score
                elif mode == "KEYWORD":
                    final_score = kw_score
                else:  # HYBRID
                    w_s, w_k, w_m = req.w_semantic, req.w_keyword, req.w_metadata
                    total_w = max(0.0001, w_s + w_k + w_m)
                    final_score = (w_s * sem_score + w_k * kw_score + w_m * meta_score) / total_w

                if final_score < 0.04:
                    continue

                why_parts = []
                if sem_score >= 0.45:
                    why_parts.append(f"Semantic match ({sem_score:.2f})")
                if kw_score > 0:
                    why_parts.append(f"Keyword match ({kw_score * 100:.0f}%)")
                why_text = f"Document chunk: {' • '.join(why_parts) if why_parts else f'{final_score:.2f}'}"

                scored_candidates.append(
                    RetrievalResult(
                        id=f"doc-{doc.id}-chunk-{chunk.chunk_index}",
                        result_type="DOCUMENT",
                        title=f"{doc.file_name} (Page {chunk.page_number})",
                        content=chunk.text_content,
                        score=round(final_score, 4),
                        semantic_score=round(sem_score, 4),
                        keyword_score=round(kw_score, 4),
                        metadata_score=round(meta_score, 4),
                        source_type="DOCUMENT",
                        source_id=doc.document_id,
                        project_id=None,
                        project_name=None,
                        page_number=chunk.page_number,
                        chunk_index=chunk.chunk_index,
                        why_matched=why_text,
                        created_at=chunk.created_at.isoformat() if chunk.created_at else None,
                        metadata={"document_id": doc.document_id, "file_name": doc.file_name},
                    )
                )

        # 4. Sort by combined score descending and slice top_k
        scored_candidates.sort(key=lambda r: r.score, reverse=True)
        top_results = scored_candidates[: req.top_k]

        search_latency_ms = (time.perf_counter() - search_start) * 1000.0
        total_ms = (time.perf_counter() - total_start) * 1000.0

        return MemorySearchResponse(
            query=query_str,
            search_mode=req.search_mode,
            total_results=len(top_results),
            results=top_results,
            query_embed_ms=round(query_embed_ms, 2),
            search_latency_ms=round(search_latency_ms, 2),
            total_ms=round(total_ms, 2),
        )


retriever = MemoryRetriever()
