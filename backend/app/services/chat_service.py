from __future__ import annotations

import datetime as dt
import logging
import time
from typing import Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai.memory.retriever import MemoryRetriever
from app.ai.reasoning.context_builder import ContextBuilder
from app.ai.reasoning.engine import ReasoningEngine
from app.database.models import (
    Attachment,
    Conversation,
    ConversationMessage,
    Document,
    DocumentPage,
    Memory,
    Project,
)
from app.schemas.chat import (
    ChatMessageRead,
    ChatMessageRequest,
    ChatResponse,
    ConversationCreate,
    ConversationRead,
    SourceAttribution,
    TimingMetrics,
    VerificationInfo,
)
from app.schemas.memory import MemorySearchQuery
from app.schemas.ocr import OCRAnalyzeRequest
from app.schemas.vision import VisionAnalyzeRequest
from app.services.ocr_service import OCRService
from app.services.vision_service import VisionService
from app.ai.vision.tracking.workspace_state import workspace_state

logger = logging.getLogger(__name__)


class ChatService:
    """
    Core Conversation Engine orchestrating:
    1. Multimodal context retrieval (hybrid memory + document search)
    2. Visual object detection & OCR extraction
    3. Injection-safe context building with priority & budget pruning
    4. Reasoning model execution (Qwen3-VL target / Local CPU host)
    5. Output validation & source attribution
    6. Conversation persistence
    """

    def __init__(
        self,
        reasoning_engine: ReasoningEngine | None = None,
        context_builder: ContextBuilder | None = None,
        memory_retriever: MemoryRetriever | None = None,
        vision_service: VisionService | None = None,
        ocr_service: OCRService | None = None,
    ) -> None:
        self.reasoning_engine = reasoning_engine or ReasoningEngine.get_instance()
        self.context_builder = context_builder or ContextBuilder()
        self.memory_retriever = memory_retriever or MemoryRetriever()
        self.vision_service = vision_service or VisionService()
        self.ocr_service = ocr_service or OCRService()

    def list_conversations(self, db: Session) -> list[ConversationRead]:
        convs = db.query(Conversation).order_by(Conversation.updated_at.desc()).all()
        return [
            ConversationRead(
                id=c.id,
                title=c.title,
                created_at=c.created_at,
                updated_at=c.updated_at,
                message_count=len(c.messages),
            )
            for c in convs
        ]

    def create_conversation(self, db: Session, payload: ConversationCreate) -> ConversationRead:
        conv = Conversation(title=payload.title)
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return ConversationRead(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=0,
        )

    def get_messages(self, db: Session, conversation_id: int) -> list[ChatMessageRead]:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found.",
            )
        return [
            ChatMessageRead(
                id=m.id,
                conversation_id=m.conversation_id,
                role=m.role,
                content=m.content,
                metadata=m.metadata_json or {},
                created_at=m.created_at,
            )
            for m in conv.messages
        ]

    def process_message(self, db: Session, payload: ChatMessageRequest) -> ChatResponse:
        t0_total = time.perf_counter()

        # 1. Resolve or create conversation
        if payload.conversation_id:
            conv = db.query(Conversation).filter(Conversation.id == payload.conversation_id).first()
            if not conv:
                conv = Conversation(title=payload.text[:40] + ("..." if len(payload.text) > 40 else ""))
                db.add(conv)
                db.commit()
                db.refresh(conv)
        else:
            conv = Conversation(title=payload.text[:40] + ("..." if len(payload.text) > 40 else ""))
            db.add(conv)
            db.commit()
            db.refresh(conv)

        # 2. Store user message in DB
        user_meta = {
            "context": payload.context,
            "has_image": bool(payload.image_context or payload.image_id),
            "image_id": payload.image_id,
            "document_id": payload.document_id,
            "memory_id": payload.memory_id,
            "project_id": payload.project_id,
        }
        user_msg = ConversationMessage(
            conversation_id=conv.id,
            role="user",
            content=payload.text,
            metadata_json=user_meta,
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        # 3. Retrieval-First Stage (Section 9)
        t_ret_start = time.perf_counter()
        retrieved_memories: list[dict[str, Any]] = []
        retrieved_document_chunks: list[dict[str, Any]] = []
        selected_doc_info: dict[str, Any] | None = None
        selected_proj_info: dict[str, Any] | None = None

        # Resolve selected project if any
        if payload.project_id:
            proj = db.query(Project).filter(Project.id == payload.project_id).first()
            if proj:
                selected_proj_info = {"id": proj.id, "name": proj.name}

        # Explicit Memory attachment
        if payload.memory_id:
            mem = db.query(Memory).filter(Memory.id == payload.memory_id).first()
            if mem:
                retrieved_memories.append({
                    "id": mem.id,
                    "title": mem.title,
                    "content": mem.content,
                    "project_id": mem.project_id,
                    "score": 1.0,
                })

        # Explicit Document attachment
        if payload.document_id:
            doc = db.query(Document).filter(
                (Document.document_id == payload.document_id) | (Document.id == payload.document_id)
            ).first()
            if doc:
                doc_text = doc.extracted_text
                page_num = payload.page_number or 1
                if payload.page_number:
                    page = db.query(DocumentPage).filter(
                        DocumentPage.document_id == doc.document_id,
                        DocumentPage.page_number == payload.page_number,
                    ).first()
                    if page and page.text:
                        doc_text = page.text
                selected_doc_info = {
                    "document_id": doc.document_id,
                    "title": doc.file_name,
                    "page": page_num,
                    "text": doc_text,
                }

        # Hybrid search over memories and documents
        try:
            search_query = MemorySearchQuery(
                query=payload.text,
                project_id=payload.project_id,
                top_k=4,
                include_documents=True,
                search_mode="HYBRID",
            )
            search_res = self.memory_retriever.search(db, search_query)
            for hit in search_res.results:
                if hit.result_type == "MEMORY" or hit.item_type == "memory":
                    # Avoid duplicate if already explicitly attached
                    if not any(m["id"] == hit.id for m in retrieved_memories):
                        retrieved_memories.append({
                            "id": hit.id,
                            "title": hit.title,
                            "content": hit.content,
                            "project_id": hit.project_id,
                            "score": hit.score,
                        })
                elif hit.result_type == "DOCUMENT" or hit.item_type == "document_chunk":
                    retrieved_document_chunks.append({
                        "document_id": hit.source_id or hit.id,
                        "title": hit.title,
                        "page": hit.page_number or 1,
                        "chunk_index": hit.chunk_index or 0,
                        "content": hit.content,
                        "project_id": hit.project_id,
                        "score": hit.score,
                    })
        except Exception as e:
            logger.warning("Memory/document retrieval encounter: %s", e)

        retrieval_ms = (time.perf_counter() - t_ret_start) * 1000

        # 4. Image & OCR Stage (Section 17, 20)
        t_img_start = time.perf_counter()
        vision_detections: list[dict[str, Any]] = []
        ocr_results: list[dict[str, Any]] = []
        attached_image_ref = payload.image_context or payload.image_id

        if attached_image_ref:
            # Attempt YOLO-X detection
            try:
                vis_req = VisionAnalyzeRequest(
                    file_id=payload.image_id if payload.image_id else None,
                    image=payload.image_context if not payload.image_id else None,
                    confidence_threshold=0.25,
                )
                vis_out = self.vision_service.analyze_frame(vis_req, db=db)
                if "detections" in vis_out:
                    for d in vis_out["detections"]:
                        vision_detections.append({
                            "label": getattr(d, "label", str(d.get("label", ""))),
                            "confidence": getattr(d, "confidence", float(d.get("confidence", 0.0))),
                            "bbox": getattr(d, "box_2d", d.get("bbox", {})),
                        })
            except Exception as e:
                logger.debug("Vision detection skipped or failed: %s", e)

            # Attempt OCR text extraction
            try:
                ocr_req = OCRAnalyzeRequest(
                    file_id=payload.image_id if payload.image_id else None,
                    image=payload.image_context if not payload.image_id else None,
                    confidence_threshold=0.2,
                )
                ocr_out = self.ocr_service.analyze_image(ocr_req, db=db)
                if hasattr(ocr_out, "regions"):
                    for r in ocr_out.regions:
                        ocr_results.append({
                            "text": r.text,
                            "confidence": r.confidence,
                            "bbox": r.bbox.model_dump() if hasattr(r.bbox, "model_dump") else {},
                        })
            except Exception as e:
                logger.debug("OCR extraction skipped or failed: %s", e)

        image_prepare_ms = (time.perf_counter() - t_img_start) * 1000

        # 5. Context Building Stage (Section 8, 10, 11, 12, 13, 22)
        t_ctx_start = time.perf_counter()
        recent_messages = (
            db.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conv.id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(6)
            .all()
        )
        recent_conv_context = [
            {"role": m.role, "content": m.content}
            for m in reversed(recent_messages)
            if m.id != user_msg.id  # Exclude current message
        ]

        # Fetch recent workspace observations if any exist
        workspace_obs = None
        try:
            raw_obs = workspace_state.get_recent_observations()
            if raw_obs:
                workspace_obs = [
                    o.model_dump() for o in raw_obs
                    if payload.project_id is None or o.project_id is None or o.project_id == payload.project_id
                ]
        except Exception as e:
            logger.debug("Failed to retrieve workspace observations for chat: %s", e)

        built_context = self.context_builder.build_context(
            user_question=payload.text,
            optional_current_image=attached_image_ref,
            vision_detections=vision_detections if vision_detections else None,
            ocr_results=ocr_results if ocr_results else None,
            selected_document=selected_doc_info,
            retrieved_memories=retrieved_memories if retrieved_memories else None,
            retrieved_document_chunks=retrieved_document_chunks if retrieved_document_chunks else None,
            selected_project=selected_proj_info,
            recent_conversation_context=recent_conv_context,
            workspace_observations=workspace_obs if workspace_obs else None,
        )
        context_build_ms = (time.perf_counter() - t_ctx_start) * 1000

        # 6. Model Reasoning Stage (Section 5, 14, 15, 16)
        validated_resp = self.reasoning_engine.run_reasoning(
            built_context=built_context,
            images=[attached_image_ref] if attached_image_ref else None,
            retrieval_ms=retrieval_ms,
            context_build_ms=context_build_ms,
            image_prepare_ms=image_prepare_ms,
        )

        # 7. Grounding Action Resolution (Step 7)
        from app.services.sentinel_orchestrator import sentinel_orchestrator
        grounding_action = sentinel_orchestrator.resolve_grounding_action(
            query=payload.text,
            is_demo=getattr(payload, "mode", "live").lower() == "demo",
            evidence=[],
            response_text=validated_resp.answer,
        )

        mode_label = "DEMO / SIMULATION" if getattr(payload, "mode", "live").lower() == "demo" else "LIVE"

        # 8. Assistant Response Persistence
        asst_meta = {
            "status": validated_resp.status,
            "mode": mode_label,
            "model": validated_resp.model_name,
            "runtime": validated_resp.runtime_name,
            "provider": validated_resp.provider_name,
            "device": validated_resp.device_name,
            "npu_verified": validated_resp.npu_verified,
            "action": grounding_action.model_dump(),
            "sources": [s.model_dump() for s in validated_resp.sources],
            "context_summary": built_context.summary.model_dump(),
            "timing": validated_resp.timing.model_dump(),
            "validation_errors": validated_resp.validation_errors,
        }
        asst_msg = ConversationMessage(
            conversation_id=conv.id,
            role="assistant",
            content=validated_resp.answer,
            metadata_json=asst_meta,
        )
        db.add(asst_msg)
        conv.updated_at = dt.datetime.now(dt.timezone.utc)
        db.commit()
        db.refresh(asst_msg)

        citation_strings = [
            f"{s.type}: {s.title}" + (f" (p.{s.page})" if s.page else "")
            for s in validated_resp.sources
        ]

        return ChatResponse(
            conversation_id=conv.id,
            user_message_id=user_msg.id,
            assistant_message_id=asst_msg.id,
            response=validated_resp.answer,
            answer=validated_resp.answer,
            status=validated_resp.status,
            mode=mode_label,
            action=grounding_action.model_dump(),
            sources=validated_resp.sources,
            citations=citation_strings,
            context_used=built_context.summary,
            model=validated_resp.model_name,
            runtime=validated_resp.runtime_name,
            timing=validated_resp.timing,
            verification=VerificationInfo(
                current_device=validated_resp.device_name,
                target_device="Snapdragon X-series / Hexagon NPU",
                npu_verified=validated_resp.npu_verified,
                status="NOT VERIFIED" if not validated_resp.npu_verified else "VERIFIED",
            ),
            metadata=asst_meta,
            created_at=asst_msg.created_at,
        )



chat_service = ChatService()
