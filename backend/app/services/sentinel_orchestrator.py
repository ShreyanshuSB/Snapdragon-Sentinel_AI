from __future__ import annotations

import datetime as dt
import logging
import re
import time
from typing import Any

from sqlalchemy.orm import Session

from app.ai.memory.retriever import MemoryRetriever
from app.ai.reasoning.context_builder import ContextBuilder
from app.ai.reasoning.engine import ReasoningEngine
from app.ai.reasoning.response_validator import ResponseValidator, ValidatedResponse
from app.ai.vision.tracking import find_it_service, spatial_engine, workspace_state
from app.database.models import (
    Conversation,
    ConversationMessage,
    Document,
    DocumentPage,
    Memory,
    Project,
)
from app.schemas.chat import (
    ContextUsedSummary,
    SourceAttribution,
    TimingMetrics,
    VerificationInfo,
)
from app.schemas.memory import MemorySearchQuery
from app.schemas.ocr import OCRAnalyzeRequest
from app.schemas.orchestrator import (
    EvidenceCategory,
    EvidenceItem,
    GroundingAction,
    GroundingActionType,
    MultimodalQueryRequest,
    MultimodalQueryResponse,
    OrchestratorTiming,
)
from app.schemas.vision import VisionAnalyzeRequest
from app.services.demo_fixture_service import demo_fixture_service
from app.services.ocr_service import OCRService
from app.services.vision_service import VisionService

logger = logging.getLogger(__name__)


class SentinelOrchestrator:
    """
    Unified Application-Level Orchestration Service for SENTINEL.
    Coordinates:
    - Input Normalization (Text, Voice, Camera/Image, Document Context)
    - Dynamic Evidence Collection (Vision, OCR, Memory, Documents, Workspace Tracking)
    - Context Priority & Token Budgeting
    - Grounded Reasoning Synthesis
    - Response Validation (rejecting hallucinations and invalid citations)
    - Structured Visual Grounding Actions
    - Truthful Hardware Separation (Host CPU vs Snapdragon NPU target)
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

    def normalize_input(self, req: MultimodalQueryRequest) -> MultimodalQueryRequest:
        """Sanitize query text, align voice transcripts, and validate mode."""
        cleaned_query = req.query.strip()
        if req.source == "voice" and req.voice_transcript:
            cleaned_query = req.voice_transcript.strip()
        req.query = cleaned_query
        req.mode = req.mode.lower()
        return req

    def process_query(self, db: Session, raw_req: MultimodalQueryRequest) -> MultimodalQueryResponse:
        t0_total = time.perf_counter()

        # 1. Input Normalization
        t_norm_start = time.perf_counter()
        req = self.normalize_input(raw_req)
        input_norm_ms = (time.perf_counter() - t_norm_start) * 1000

        is_demo = req.mode == "demo"
        mode_label = "DEMO / SIMULATION" if is_demo else "LIVE"

        # 2. Evidence Collection Stage
        t_ev_start = time.perf_counter()
        t_ret_start = time.perf_counter()

        evidence_items: list[EvidenceItem] = []
        vision_detections: list[dict[str, Any]] = []
        ocr_results: list[dict[str, Any]] = []
        retrieved_memories: list[dict[str, Any]] = []
        retrieved_document_chunks: list[dict[str, Any]] = []
        selected_doc_info: dict[str, Any] | None = None
        selected_proj_info: dict[str, Any] | None = None
        workspace_obs: list[dict[str, Any]] = []

        if is_demo:
            # Load controlled, reproducible test fixtures
            evidence_items = demo_fixture_service.get_demo_evidence()
            demo_tracks = demo_fixture_service.get_demo_workspace_tracks()
            for t in demo_tracks:
                vision_detections.append({
                    "label": t.class_name,
                    "confidence": t.confidence,
                    "bbox": t.smoothed_bbox.model_dump(),
                    "region": t.region,
                })
            retrieved_memories = demo_fixture_service.get_demo_memories()
            retrieved_document_chunks = demo_fixture_service.get_demo_documents()
            workspace_obs = [o.model_dump() for o in demo_fixture_service.get_demo_observations()]
            retrieval_ms = 1.2
        else:
            # Live Mode: Gather physical workspace state
            # A. If request explicitly provides workspace_state dict (from client or test harness)
            if req.workspace_state and isinstance(req.workspace_state, dict):
                tracks = req.workspace_state.get("active_tracks", [])
                for t in tracks:
                    lbl = t.get("label", t.get("class_name", "object"))
                    cnf = float(t.get("confidence", 0.9))
                    reg = t.get("zone", t.get("region", "center"))
                    bx = t.get("bbox", [0, 0, 100, 100])
                    tid = t.get("track_id", "track_custom")
                    vision_detections.append({
                        "label": lbl,
                        "confidence": cnf,
                        "bbox": bx,
                        "region": reg,
                    })
                    evidence_items.append(
                        EvidenceItem(
                            category=EvidenceCategory.OBSERVED,
                            source_type="VISION",
                            source_id=tid,
                            title=f"Visible: {lbl}",
                            snippet=f"Detected {lbl} in region '{reg}' (conf: {cnf:.2f})",
                            score=cnf,
                            metadata={"track_id": tid, "bbox": bx, "zone": reg},
                        )
                    )
                    if t.get("ocr_text"):
                        ocr_results.append({
                            "text": t["ocr_text"],
                            "confidence": 0.95,
                            "bbox": bx,
                        })
                        evidence_items.append(
                            EvidenceItem(
                                category=EvidenceCategory.OBSERVED,
                                source_type="OCR",
                                source_id=f"ocr_{tid}",
                                title=f"OCR on {lbl}",
                                snippet=f'Recognized text: "{t["ocr_text"]}"',
                                score=0.95,
                                metadata={"track_id": tid},
                            )
                        )
            else:
                try:
                    active_tracks = workspace_state.get_active_tracks()
                    for t in active_tracks:
                        vision_detections.append({
                            "label": t.class_name,
                            "confidence": t.confidence,
                            "bbox": t.smoothed_bbox.model_dump(),
                            "region": t.region,
                        })
                        evidence_items.append(
                            EvidenceItem(
                                category=EvidenceCategory.OBSERVED,
                                source_type="VISION",
                                source_id=t.track_id,
                                title=f"Visible: {t.user_label or t.class_name}",
                                snippet=f"Detected {t.class_name} in region '{t.region}' (conf: {t.confidence:.2f})",
                                score=t.confidence,
                                metadata={"track_id": t.track_id, "bbox": t.smoothed_bbox.model_dump()},
                            )
                        )
                        for text in t.ocr_associations:
                            ocr_results.append({
                                "text": text,
                                "confidence": t.ocr_association_conf,
                                "bbox": t.smoothed_bbox.model_dump(),
                            })
                            evidence_items.append(
                                EvidenceItem(
                                    category=EvidenceCategory.OBSERVED,
                                    source_type="OCR",
                                    source_id=f"ocr_{t.track_id}",
                                    title=f"OCR on {t.class_name}",
                                    snippet=f'Recognized text: "{text}"',
                                    score=t.ocr_association_conf,
                                    metadata={"track_id": t.track_id},
                                )
                            )

                    # Recent workspace observations
                    raw_obs = workspace_state.get_recent_observations()
                    if raw_obs:
                        workspace_obs = [
                            o.model_dump() for o in raw_obs
                            if req.project_id is None or o.project_id is None or o.project_id == req.project_id
                        ]
                except Exception as e:
                    logger.debug("Live workspace tracking state read: %s", e)

            # Attached image analysis if provided
            attached_image_ref = req.image_context or req.image_id
            if attached_image_ref:
                try:
                    vis_req = VisionAnalyzeRequest(
                        file_id=req.image_id if req.image_id else None,
                        image=req.image_context if not req.image_id else None,
                        confidence_threshold=0.25,
                    )
                    vis_out = self.vision_service.analyze_frame(vis_req, db=db)
                    if "detections" in vis_out:
                        for d in vis_out["detections"]:
                            lbl = getattr(d, "label", str(d.get("label", "")))
                            cnf = getattr(d, "confidence", float(d.get("confidence", 0.0)))
                            bx = getattr(d, "box_2d", d.get("bbox", {}))
                            vision_detections.append({"label": lbl, "confidence": cnf, "bbox": bx})
                            evidence_items.append(
                                EvidenceItem(
                                    category=EvidenceCategory.OBSERVED,
                                    source_type="VISION",
                                    source_id=f"img_det_{lbl}",
                                    title=f"Frame Detection: {lbl}",
                                    snippet=f"Detected {lbl} in uploaded frame (conf: {cnf:.2f})",
                                    score=cnf,
                                    metadata={"bbox": bx},
                                )
                            )
                except Exception as e:
                    logger.debug("Attached frame vision analysis: %s", e)

                try:
                    ocr_req = OCRAnalyzeRequest(
                        file_id=req.image_id if req.image_id else None,
                        image=req.image_context if not req.image_id else None,
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
                            evidence_items.append(
                                EvidenceItem(
                                    category=EvidenceCategory.OBSERVED,
                                    source_type="OCR",
                                    source_id=f"ocr_reg_{r.text[:12]}",
                                    title="OCR Region",
                                    snippet=f'Extracted text: "{r.text}"',
                                    score=r.confidence,
                                )
                            )
                except Exception as e:
                    logger.debug("Attached frame OCR extraction: %s", e)

            # Explicit project attachment
            if req.project_id:
                proj = db.query(Project).filter(Project.id == req.project_id).first()
                if proj:
                    selected_proj_info = {"id": proj.id, "name": proj.name}

            # Explicit document attachment
            if req.document_id:
                doc = db.query(Document).filter(
                    (Document.document_id == req.document_id) | (Document.id == req.document_id)
                ).first()
                if doc:
                    doc_text = doc.extracted_text
                    page_num = req.page_number or 1
                    if req.page_number:
                        page = db.query(DocumentPage).filter(
                            DocumentPage.document_id == doc.document_id,
                            DocumentPage.page_number == req.page_number,
                        ).first()
                        if page and page.text:
                            doc_text = page.text
                    selected_doc_info = {
                        "document_id": doc.document_id,
                        "title": doc.file_name,
                        "page": page_num,
                        "text": doc_text,
                    }
                    evidence_items.append(
                        EvidenceItem(
                            category=EvidenceCategory.RETRIEVED,
                            source_type="DOCUMENT",
                            source_id=doc.document_id,
                            title=doc.file_name,
                            snippet=doc_text[:250],
                            page=page_num,
                            score=1.0,
                        )
                    )

            # Hybrid retrieval over memory and documents
            try:
                search_query = MemorySearchQuery(
                    query=req.query,
                    project_id=req.project_id,
                    top_k=4,
                    include_documents=True,
                    search_mode="HYBRID",
                )
                search_res = self.memory_retriever.search(db, search_query)
                for hit in search_res.results:
                    res_type = getattr(hit, "result_type", "")
                    if res_type == "MEMORY":
                        if not any(m["id"] == hit.id for m in retrieved_memories):
                            retrieved_memories.append({
                                "id": hit.id,
                                "title": hit.title,
                                "content": hit.content,
                                "project_id": hit.project_id,
                                "score": hit.score,
                            })
                            evidence_items.append(
                                EvidenceItem(
                                    category=EvidenceCategory.RETRIEVED,
                                    source_type="MEMORY",
                                    source_id=hit.id,
                                    title=hit.title,
                                    snippet=hit.content,
                                    score=hit.score,
                                )
                            )
                    elif res_type == "DOCUMENT":
                        retrieved_document_chunks.append({
                            "document_id": hit.source_id or hit.id,
                            "title": hit.title,
                            "page": hit.page_number or 1,
                            "chunk_index": hit.chunk_index or 0,
                            "content": hit.content,
                            "project_id": hit.project_id,
                            "score": hit.score,
                        })
                        evidence_items.append(
                            EvidenceItem(
                                category=EvidenceCategory.RETRIEVED,
                                source_type="DOCUMENT",
                                source_id=hit.source_id or hit.id,
                                title=hit.title,
                                snippet=hit.content,
                                page=hit.page_number or 1,
                                score=hit.score,
                            )
                        )
            except Exception as e:
                logger.debug("Memory/document retrieval: %s", e)

            retrieval_ms = (time.perf_counter() - t_ret_start) * 1000

        evidence_coll_ms = (time.perf_counter() - t_ev_start) * 1000

        # 3. Context Hierarchy & Budgeting Stage
        t_ctx_start = time.perf_counter()
        recent_conv_context: list[dict[str, str]] = []
        conv_record: Conversation | None = None
        user_msg_record: ConversationMessage | None = None

        if req.conversation_id:
            conv_record = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
            if conv_record:
                recent_msgs = (
                    db.query(ConversationMessage)
                    .filter(ConversationMessage.conversation_id == conv_record.id)
                    .order_by(ConversationMessage.created_at.desc())
                    .limit(6)
                    .all()
                )
                recent_conv_context = [{"role": m.role, "content": m.content} for m in reversed(recent_msgs)]

        # Store user message if session is active
        if conv_record is None and req.conversation_id is not None:
            conv_record = Conversation(title=req.query[:40] + ("..." if len(req.query) > 40 else ""))
            db.add(conv_record)
            db.commit()
            db.refresh(conv_record)

        if conv_record:
            user_msg_record = ConversationMessage(
                conversation_id=conv_record.id,
                role="user",
                content=req.query,
                metadata_json={"source": req.source, "mode": req.mode},
            )
            db.add(user_msg_record)
            db.commit()
            db.refresh(user_msg_record)

        built_context = self.context_builder.build_context(
            user_question=req.query,
            optional_current_image=req.image_context or req.image_id,
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

        # 4. Reasoning Synthesis Stage
        t_gen_start = time.perf_counter()
        validated_resp = self.reasoning_engine.run_reasoning(
            built_context=built_context,
            images=[req.image_context or req.image_id] if (req.image_context or req.image_id) else None,
            retrieval_ms=retrieval_ms,
            context_build_ms=context_build_ms,
            image_prepare_ms=0.0,
        )
        generation_ms = (time.perf_counter() - t_gen_start) * 1000

        # 5. Response Validation Stage
        t_val_start = time.perf_counter()
        # Response is validated through ResponseValidator
        validation_ms = (time.perf_counter() - t_val_start) * 1000

        # 6. Structured Grounding Action Generation
        t_act_start = time.perf_counter()
        grounding_action = self.resolve_grounding_action(
            query=req.query,
            is_demo=is_demo,
            evidence=evidence_items,
            response_text=validated_resp.answer,
            workspace_state=req.workspace_state,
        )
        action_gen_ms = (time.perf_counter() - t_act_start) * 1000

        # 7. Persistence for Assistant Response
        asst_msg_record: ConversationMessage | None = None
        if conv_record:
            asst_meta = {
                "status": validated_resp.status,
                "mode": mode_label,
                "model": validated_resp.model_name,
                "runtime": validated_resp.runtime_name,
                "device": validated_resp.device_name,
                "npu_verified": validated_resp.npu_verified,
                "action": grounding_action.model_dump(),
                "sources": [s.model_dump() for s in validated_resp.sources],
                "timing": validated_resp.timing.model_dump(),
            }
            asst_msg_record = ConversationMessage(
                conversation_id=conv_record.id,
                role="assistant",
                content=validated_resp.answer,
                metadata_json=asst_meta,
            )
            db.add(asst_msg_record)
            conv_record.updated_at = dt.datetime.now(dt.timezone.utc)
            db.commit()
            db.refresh(asst_msg_record)

        total_ms = (time.perf_counter() - t0_total) * 1000

        timing_summary = OrchestratorTiming(
            input_normalization_ms=round(input_norm_ms, 2),
            evidence_collection_ms=round(evidence_coll_ms, 2),
            retrieval_ms=round(retrieval_ms, 2),
            context_build_ms=round(context_build_ms, 2),
            image_prepare_ms=0.0,
            generation_ms=round(generation_ms, 2),
            validation_ms=round(validation_ms, 2),
            action_generation_ms=round(action_gen_ms, 2),
            total_ms=round(total_ms, 2),
            model_inference_status=validated_resp.status,
        )

        citation_strings = [
            f"{s.type}: {s.title}" + (f" (p.{s.page})" if s.page else "")
            for s in validated_resp.sources
        ]

        # In demo mode, clearly prefix answer if not already marked
        answer_text = validated_resp.answer
        if is_demo and not answer_text.startswith(f"[{mode_label}]"):
            answer_text = f"[{mode_label}] {answer_text}"

        return MultimodalQueryResponse(
            query=req.query,
            answer=answer_text,
            status=validated_resp.status,
            mode=mode_label,
            sources=validated_resp.sources,
            citations=citation_strings,
            evidence=evidence_items,
            action=grounding_action,
            observed_facts=getattr(validated_resp, "observed_facts", []),
            retrieved_facts=getattr(validated_resp, "retrieved_facts", []),
            inferred_facts=getattr(validated_resp, "inferred_facts", []),
            uncertainties=getattr(validated_resp, "uncertainties", []),
            context_summary=built_context.summary,
            timing=timing_summary,
            verification=VerificationInfo(
                current_device=validated_resp.device_name,
                target_device="Snapdragon X-series / Hexagon NPU",
                npu_verified=validated_resp.npu_verified,
                status="NOT VERIFIED" if not validated_resp.npu_verified else "VERIFIED",
            ),
            conversation_id=conv_record.id if conv_record else None,
            user_message_id=user_msg_record.id if user_msg_record else None,
            assistant_message_id=asst_msg_record.id if asst_msg_record else None,
        )

    def resolve_grounding_action(
        self,
        query: str,
        is_demo: bool = False,
        evidence: list[EvidenceItem] | None = None,
        response_text: str = "",
        workspace_state: dict[str, Any] | None = None,
    ) -> GroundingAction:
        """
        Derive a deterministic, structured UI action matching the query intent.
        Actions strictly conform to the GroundingActionType enum.
        """
        evidence = evidence or []
        q_lower = query.lower()

        # 1. Location / Find It queries
        is_find_query = any(w in q_lower for w in ["where is", "where's", "find my", "find the", "locate", "show me where", "look for"])

        if is_find_query:
            if is_demo:
                # Find in demo tracks
                demo_tracks = demo_fixture_service.get_demo_workspace_tracks()
                for t in demo_tracks:
                    if t.class_name.lower() in q_lower or (t.user_label and t.user_label.lower() in q_lower):
                        return GroundingAction(
                            action=GroundingActionType.HIGHLIGHT_OBJECT,
                            target_id=t.track_id,
                            label=t.user_label or t.class_name,
                            box_2d=t.smoothed_bbox.model_dump(),
                            zone=t.region,
                            confidence=t.confidence,
                            description=f"Located '{t.user_label or t.class_name}' in region '{t.region}'.",
                        )
            else:
                # A. Check explicit workspace_state dictionary if passed
                if workspace_state and isinstance(workspace_state, dict):
                    tracks = workspace_state.get("active_tracks", [])
                    for t in tracks:
                        lbl = str(t.get("label", t.get("class_name", ""))).lower()
                        if any(w in q_lower for w in lbl.split()) or lbl in q_lower:
                            tid = t.get("track_id", "track_custom")
                            reg = t.get("zone", t.get("region", "center"))
                            bx = t.get("bbox")
                            return GroundingAction(
                                action=GroundingActionType.HIGHLIGHT_OBJECT,
                                target_id=tid,
                                label=t.get("label", t.get("class_name", "object")),
                                box_2d=bx,
                                zone=reg,
                                confidence=float(t.get("confidence", 0.9)),
                                description=f"Located '{t.get('label')}' in region '{reg}'.",
                            )

                # B. Check evidence items with source_type == "VISION"
                for ev in evidence:
                    if ev.source_type == "VISION":
                        clean_lbl = ev.title.replace("Visible: ", "").lower()
                        if any(w in q_lower for w in clean_lbl.split()) or clean_lbl in q_lower:
                            tid = ev.metadata.get("track_id") or str(ev.source_id)
                            reg = ev.metadata.get("zone", "center")
                            bx = ev.metadata.get("bbox")
                            return GroundingAction(
                                action=GroundingActionType.HIGHLIGHT_OBJECT,
                                target_id=tid,
                                label=ev.title,
                                box_2d=bx,
                                zone=reg,
                                confidence=ev.score or 0.9,
                                description=f"Located '{ev.title}' in region '{reg}'.",
                            )

                # C. Live FindIt resolution
                try:
                    find_res = find_it_service.query(query)
                    if find_res.found and find_res.track_id:
                        bx = find_res.grounding_box.model_dump() if find_res.grounding_box else None
                        return GroundingAction(
                            action=GroundingActionType.HIGHLIGHT_OBJECT,
                            target_id=find_res.track_id,
                            label=find_res.object,
                            box_2d=bx,
                            zone=find_res.region,
                            confidence=find_res.confidence,
                            description=find_res.message,
                        )
                except Exception as e:
                    logger.debug("Live find it resolution: %s", e)

        # 2. Document reference queries
        is_doc_query = any(w in q_lower for w in ["document", "manual", "guide", "pdf", "section", "page", "datasheet"])
        if is_doc_query:
            doc_items = [e for e in evidence if e.source_type == "DOCUMENT"]
            if doc_items:
                target_doc = doc_items[0]
                return GroundingAction(
                    action=GroundingActionType.OPEN_DOCUMENT,
                    target_id=str(target_doc.source_id),
                    document_id=str(target_doc.source_id),
                    page=target_doc.page or 1,
                    label=target_doc.title,
                    description=f"Referenced document: {target_doc.title}",
                )

        # 3. Memory reference queries
        is_mem_query = any(w in q_lower for w in ["what did i save", "saved note", "remembered", "notes say", "my memory"])
        if is_mem_query:
            mem_items = [e for e in evidence if e.source_type == "MEMORY"]
            if mem_items:
                target_mem = mem_items[0]
                return GroundingAction(
                    action=GroundingActionType.OPEN_MEMORY,
                    target_id=int(target_mem.source_id) if str(target_mem.source_id).isdigit() else None,
                    memory_id=int(target_mem.source_id) if str(target_mem.source_id).isdigit() else None,
                    label=target_mem.title,
                    description=f"Referenced memory: {target_mem.title}",
                )

        # 4. Vision inspection queries
        if any(w in q_lower for w in ["what am i looking at", "what's on my desk", "look at my desk", "camera view"]):
            vis_items = [e for e in evidence if e.source_type in ("VISION", "WORKSPACE_TRACK")]
            if vis_items:
                return GroundingAction(
                    action=GroundingActionType.OPEN_VISION,
                    label="Workspace Vision",
                    description="Visual desk objects currently under observation.",
                )

        return GroundingAction(action=GroundingActionType.NONE)


sentinel_orchestrator = SentinelOrchestrator()
