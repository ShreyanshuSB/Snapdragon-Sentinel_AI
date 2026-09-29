from __future__ import annotations

import logging
import os
import uuid
from typing import Any
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database.models import Attachment, Document, DocumentPage
from app.schemas.document import (
    DocumentPageResponse,
    DocumentResponse,
    DocumentSearchHit,
    DocumentSearchResponse,
)
from app.schemas.ocr import TextRegion
from app.services.document_parser import document_parser

logger = logging.getLogger("sentinel.services.document_service")


class DocumentService:
    """Manages document ingestion, storage, retrieval, and full-text keyword search."""

    def ingest_document(
        self,
        file_id: str,
        force_ocr: bool = False,
        db: Session | None = None,
    ) -> DocumentResponse:
        if db is None:
            raise ValueError("Database session is required.")

        att = db.query(Attachment).filter(Attachment.file_id == file_id).first()
        if not att or not os.path.exists(att.file_path):
            raise FileNotFoundError(f"Attachment '{file_id}' not found on disk.")

        # Check if already ingested
        existing = db.query(Document).filter(Document.file_id == file_id).first()
        if existing:
            return self._to_response(existing, include_pages=True)

        # Parse document locally
        parse_result = document_parser.parse_file(
            file_path=att.file_path,
            mime_type=att.mime_type,
            force_ocr=force_ocr,
        )

        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        doc = Document(
            document_id=doc_id,
            file_id=att.file_id,
            file_name=att.file_name,
            file_path=att.file_path,
            file_size=att.file_size,
            mime_type=att.mime_type or "application/octet-stream",
            source_type=parse_result.source_type,
            status=parse_result.status,
            page_count=parse_result.page_count,
            ocr_pages_count=parse_result.ocr_pages_count,
            extracted_text=parse_result.extracted_text,
            extraction_method=parse_result.extraction_method,
            processing_time_ms=parse_result.processing_time_ms,
            metadata_json=parse_result.metadata,
        )
        db.add(doc)
        db.flush()

        # Insert pages
        for p in parse_result.pages:
            db_page = DocumentPage(
                document_id=doc_id,
                page_number=p["page_number"],
                width=p["width"],
                height=p["height"],
                text=p["text"],
                has_ocr=p["has_ocr"],
                regions_json=p["regions"],
                processing_time_ms=p["processing_time_ms"],
            )
            db.add(db_page)

        db.commit()
        db.refresh(doc)

        # Index document chunks for semantic search
        try:
            from app.ai.memory.indexer import indexer
            indexer.index_document(db, doc)
        except Exception as e:
            logger.warning("Document chunk indexing failed (text remains searchable): %s", e)

        logger.info(
            "Document '%s' (%s) ingested locally in %s ms. Pages: %d, OCR Pages: %d",
            doc.file_name,
            doc.document_id,
            doc.processing_time_ms,
            doc.page_count,
            doc.ocr_pages_count,
        )
        return self._to_response(doc, include_pages=True)

    def list_documents(
        self,
        db: Session,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DocumentResponse]:
        docs = (
            db.query(Document)
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [self._to_response(d, include_pages=False) for d in docs]

    def get_document(
        self,
        document_id: str,
        db: Session,
        include_pages: bool = True,
    ) -> DocumentResponse:
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise FileNotFoundError(f"Document '{document_id}' not found.")
        return self._to_response(doc, include_pages=include_pages)

    def get_document_pages(
        self,
        document_id: str,
        db: Session,
    ) -> list[DocumentPageResponse]:
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise FileNotFoundError(f"Document '{document_id}' not found.")

        pages = (
            db.query(DocumentPage)
            .filter(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number)
            .all()
        )
        return [self._page_to_response(p) for p in pages]

    def get_document_text(self, document_id: str, db: Session) -> dict[str, Any]:
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise FileNotFoundError(f"Document '{document_id}' not found.")
        return {
            "document_id": doc.document_id,
            "file_name": doc.file_name,
            "page_count": doc.page_count,
            "text": doc.extracted_text,
            "source_type": doc.source_type,
            "extraction_method": doc.extraction_method,
        }

    def delete_document(self, document_id: str, db: Session) -> dict[str, Any]:
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise FileNotFoundError(f"Document '{document_id}' not found.")

        # Deleting document deletes its pages through cascade in DB
        db.delete(doc)
        db.commit()
        logger.info("Document '%s' deleted from local storage.", document_id)
        return {"status": "DELETED", "document_id": document_id, "message": "Document deleted successfully."}

    def search_documents(self, query: str, db: Session) -> DocumentSearchResponse:
        clean_q = query.strip()
        if not clean_q:
            return DocumentSearchResponse(query=query, total_hits=0, results=[])

        search_pat = f"%{clean_q}%"

        # Search matching pages first for exact page attribution
        matching_pages = (
            db.query(DocumentPage, Document)
            .join(Document, DocumentPage.document_id == Document.document_id)
            .filter(DocumentPage.text.ilike(search_pat))
            .limit(50)
            .all()
        )

        hits: list[DocumentSearchHit] = []
        seen_doc_pages: set[tuple[str, int]] = set()

        for page, doc in matching_pages:
            snippet = self._generate_snippet(page.text, clean_q)
            hits.append(
                DocumentSearchHit(
                    document_id=doc.document_id,
                    file_id=doc.file_id,
                    file_name=doc.file_name,
                    page_number=page.page_number,
                    source_type=doc.source_type,
                    snippet=snippet,
                    match_count=page.text.lower().count(clean_q.lower()),
                    created_at=doc.created_at,
                )
            )
            seen_doc_pages.add((doc.document_id, page.page_number))

        # Also search document-level extracted text if not covered
        matching_docs = (
            db.query(Document)
            .filter(Document.extracted_text.ilike(search_pat))
            .limit(20)
            .all()
        )

        for doc in matching_docs:
            if not any(h.document_id == doc.document_id for h in hits):
                snippet = self._generate_snippet(doc.extracted_text, clean_q)
                hits.append(
                    DocumentSearchHit(
                        document_id=doc.document_id,
                        file_id=doc.file_id,
                        file_name=doc.file_name,
                        page_number=1,
                        source_type=doc.source_type,
                        snippet=snippet,
                        match_count=doc.extracted_text.lower().count(clean_q.lower()),
                        created_at=doc.created_at,
                    )
                )

        return DocumentSearchResponse(
            query=clean_q,
            total_hits=len(hits),
            results=hits,
        )

    def _generate_snippet(self, text: str, query: str, context_chars: int = 120) -> str:
        idx = text.lower().find(query.lower())
        if idx == -1:
            return text[:context_chars] + ("..." if len(text) > context_chars else "")

        start = max(0, idx - context_chars // 2)
        end = min(len(text), idx + len(query) + context_chars // 2)
        snippet = text[start:end].replace("\n", " ").strip()
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        return f"{prefix}{snippet}{suffix}"

    def _to_response(self, doc: Document, include_pages: bool = False) -> DocumentResponse:
        pages_resp: list[DocumentPageResponse] = []
        if include_pages and doc.pages:
            pages_resp = [self._page_to_response(p) for p in doc.pages]

        return DocumentResponse(
            document_id=doc.document_id,
            file_id=doc.file_id,
            file_name=doc.file_name,
            file_size=doc.file_size,
            mime_type=doc.mime_type,
            source_type=doc.source_type,
            status=doc.status,
            page_count=doc.page_count,
            ocr_pages_count=doc.ocr_pages_count,
            extracted_text=doc.extracted_text,
            extraction_method=doc.extraction_method,
            processing_time_ms=doc.processing_time_ms,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            pages=pages_resp,
            metadata=doc.metadata_json or {},
        )

    def _page_to_response(self, page: DocumentPage) -> DocumentPageResponse:
        raw_regions = page.regions_json or []
        typed_regions: list[TextRegion] = []
        for r in raw_regions:
            try:
                typed_regions.append(TextRegion(**r))
            except Exception:
                pass

        return DocumentPageResponse(
            page_number=page.page_number,
            width=page.width,
            height=page.height,
            text=page.text,
            has_ocr=page.has_ocr,
            regions=typed_regions,
            processing_time_ms=page.processing_time_ms,
        )


document_service = DocumentService()
