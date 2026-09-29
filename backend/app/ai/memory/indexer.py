from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.memory.chunking import chunk_text
from app.ai.memory.embedding_engine import embedding_engine
from app.database.models import Document, DocumentChunk, DocumentPage, Memory

logger = logging.getLogger(__name__)


class MemoryIndexer:
    """
    Manages indexing and idempotent reindexing of user memories and source document chunks.
    Ensures vector dimensions, model versions, and status flags remain strictly consistent.
    """

    def index_memory(self, db: Session, memory: Memory) -> None:
        """
        Generates and assigns embedding for a single memory record.
        Transitions embedding_status: PENDING/STALE -> READY (or FAILED on error).
        Does NOT delete the memory if embedding generation fails.
        """
        # Compose content for embedding: title + content + summary
        text_to_embed = f"{memory.title}\n{memory.content}"
        if memory.summary:
            text_to_embed += f"\nSummary: {memory.summary}"

        meta = embedding_engine.get_metadata()
        try:
            vec, _ = embedding_engine.embed_text(text_to_embed, is_query=False)
            memory.embedding = embedding_engine.vector_to_bytes(vec)
            memory.embedding_status = "READY"
            memory.embedding_model = meta.name
            memory.embedding_model_version = meta.version
            memory.embedding_dimension = meta.dimension
            db.commit()
            db.refresh(memory)
            logger.info("Successfully indexed memory %s ('%s').", memory.id, memory.title)
        except Exception as e:
            logger.exception("Failed to generate embedding for memory %s: %s", memory.id, e)
            memory.embedding_status = "FAILED"
            db.commit()
            db.refresh(memory)

    def reindex_all_memories(self, db: Session, force: bool = False) -> tuple[int, float]:
        """
        Reindexes all memories. If force=True, re-embeds even if already READY.
        Detects model dimension/name mismatches and updates them.
        Idempotent: running multiple times updates the existing vectors safely.

        Returns: (indexed_count, duration_ms)
        """
        t0 = time.perf_counter()
        meta = embedding_engine.get_metadata()

        stmt = select(Memory)
        if not force:
            # Reindex pending, stale, failed, or dimension/model mismatched memories
            stmt = stmt.where(
                (Memory.embedding_status != "READY")
                | (Memory.embedding == None)  # noqa: E711
                | (Memory.embedding_dimension != meta.dimension)
                | (Memory.embedding_model != meta.name)
            )

        memories = db.execute(stmt).scalars().all()
        if not memories:
            return 0, (time.perf_counter() - t0) * 1000.0

        texts = [f"{m.title}\n{m.content}" for m in memories]
        try:
            vecs, _ = embedding_engine.embed_batch(texts, is_query=False)
            for i, mem in enumerate(memories):
                mem.embedding = embedding_engine.vector_to_bytes(vecs[i])
                mem.embedding_status = "READY"
                mem.embedding_model = meta.name
                mem.embedding_model_version = meta.version
                mem.embedding_dimension = meta.dimension

            db.commit()
            duration_ms = (time.perf_counter() - t0) * 1000.0
            logger.info("Reindexed %d memories in %.2f ms.", len(memories), duration_ms)
            return len(memories), duration_ms
        except Exception as e:
            db.rollback()
            logger.exception("Reindexing memories batch failed: %s", e)
            raise

    def index_document(self, db: Session, document: Document) -> int:
        """
        Splits document pages into chunks, generates embeddings, and saves DocumentChunk records.
        Idempotent: removes any previous chunks for this document before inserting refreshed ones.
        Returns count of chunks created.
        """
        pages = db.execute(
            select(DocumentPage)
            .where(DocumentPage.document_id == document.document_id)
            .order_by(DocumentPage.page_number)
        ).scalars().all()

        if not pages:
            return 0

        # Delete any pre-existing chunks for this document to ensure idempotency
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.document_id))
        db.commit()

        all_chunks: list[dict[str, Any]] = []
        chunk_texts: list[str] = []

        global_idx = 0
        for page in pages:
            if not page.text.strip():
                continue

            page_chunks = chunk_text(page.text, chunk_size=450, overlap=50)
            for ch in page_chunks:
                # Include document name and page number for semantic context
                contextual_text = f"Document: {document.file_name} (Page {page.page_number})\n{ch['text']}"
                all_chunks.append({
                    "page_number": page.page_number,
                    "chunk_index": global_idx,
                    "text_content": ch["text"],
                    "start_char": ch["start_char"],
                    "end_char": ch["end_char"],
                })
                chunk_texts.append(contextual_text)
                global_idx += 1

        if not all_chunks:
            return 0

        meta = embedding_engine.get_metadata()
        try:
            vecs, _ = embedding_engine.embed_batch(chunk_texts, is_query=False)
            for i, ch_data in enumerate(all_chunks):
                chunk_rec = DocumentChunk(
                    document_id=document.document_id,
                    page_number=ch_data["page_number"],
                    chunk_index=ch_data["chunk_index"],
                    text_content=ch_data["text_content"],
                    embedding=embedding_engine.vector_to_bytes(vecs[i]),
                    embedding_status="READY",
                    embedding_model=meta.name,
                    embedding_model_version=meta.version,
                    embedding_dimension=meta.dimension,
                    start_char=ch_data["start_char"],
                    end_char=ch_data["end_char"],
                )
                db.add(chunk_rec)

            db.commit()
            logger.info("Indexed %d chunks for document %s.", len(all_chunks), document.file_name)
            return len(all_chunks)
        except Exception as e:
            db.rollback()
            logger.exception("Failed to embed document chunks for %s: %s", document.file_name, e)
            return 0

    def reindex_all_documents(self, db: Session) -> tuple[int, float]:
        """
        Rebuilds chunks and embeddings for all ingested documents in the system.
        """
        t0 = time.perf_counter()
        docs = db.execute(select(Document)).scalars().all()
        total_chunks = 0
        for doc in docs:
            count = self.index_document(db, doc)
            total_chunks += count

        duration_ms = (time.perf_counter() - t0) * 1000.0
        return total_chunks, duration_ms

    def reindex_all(self, db: Session, force: bool = False) -> tuple[int, int, float]:
        """
        Rebuilds all user memories and all document chunks in one idempotent operation.
        Returns: (memories_count, chunks_count, total_duration_ms)
        """
        t0 = time.perf_counter()
        mem_count, _ = self.reindex_all_memories(db, force=force)
        doc_count, _ = self.reindex_all_documents(db)
        total_ms = (time.perf_counter() - t0) * 1000.0
        return mem_count, doc_count, total_ms


indexer = MemoryIndexer()
