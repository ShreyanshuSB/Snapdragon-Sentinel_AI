from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.benchmark_manager import BenchmarkManager, benchmark_manager
from app.core.model_manager import ModelManager
from app.database.connection import SessionLocal
from app.database.models import Attachment
from app.schemas.attachment import AttachmentRead, AttachmentUploadResponse
from app.schemas.benchmark import BenchmarkRecord, BenchmarkSummary
from app.schemas.chat import (
    ChatMessageRead,
    ChatMessageRequest,
    ChatResponse,
    ConversationCreate,
    ConversationRead,
)
from app.schemas.memory import (
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    EmbeddingStatusResponse,
    MemoryCreate,
    MemoryEmbedRequest,
    MemoryEmbedResponse,
    MemoryListResponse,
    MemoryRead,
    MemorySearchQuery,
    MemorySearchResponse,
    MemoryStats,
    MemoryUpdate,
    ReindexResponse,
)
from app.schemas.privacy import PrivacyPolicy, PrivacyPolicyUpdate
from app.schemas.project import ProjectCreate, ProjectRead
from app.schemas.status import HardwareStatus, ModelStatusResponse, RuntimeStatus
from app.schemas.vision import (
    FrameCaptureRequest,
    FrameCaptureResponse,
    VisionAnalyzeRequest,
    VisionResult,
)
from app.ai.model_registry import model_registry
from app.ai.model_selector import model_selector
from app.schemas.diagnostics import (
    FullDiagnosticsResponse,
    HardwareDiagnosticsResponse,
    ModelCandidateRecord,
    ModelSelectionResponse,
    RuntimeDiagnosticsResponse,
)
from app.services.chat_service import chat_service
from app.services.environment_report import generate_environment_report
from app.services.hardware_diagnostics import hardware_diagnostics
from app.services.memory_service import memory_service
from app.services.privacy_service import privacy_service
from app.services.project_service import project_service
from app.services.runtime_diagnostics import runtime_diagnostics
from app.services.vision_service import vision_service
from app.schemas.ocr import OCRAnalyzeRequest, OCRResult, OCRStatusResponse
from app.schemas.document import (
    DocumentCreateRequest,
    DocumentPageResponse,
    DocumentResponse,
    DocumentSearchResponse,
)
from app.services.ocr_service import ocr_service
from app.services.document_service import document_service
from app.ai.vision.tracking import (
    FindItRequest,
    FindItResponse,
    RememberObjectRequest,
    TrackingSessionState,
    VisibilityState,
    WorkspaceStateResponse,
    WorkspaceTrackRequest,
    find_it_service,
    spatial_engine,
    workspace_state,
)
from app.schemas.speech import (
    MicrophoneState,
    SpeechTranscribeRequest,
    SpeechTranscribeResponse,
    VoiceBenchmarkResult,
    VoiceStatusResponse,
)
from app.services.speech_service import speech_service
from app.schemas.orchestrator import (
    MultimodalQueryRequest,
    MultimodalQueryResponse,
)
from app.services.sentinel_orchestrator import sentinel_orchestrator
from app.services.demo_fixture_service import demo_fixture_service

router = APIRouter()
model_manager = ModelManager()



def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Health & Status
# ---------------------------------------------------------------------------
@router.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "SENTINEL Backend",
        "phase": "Phase 1 — Foundation",
        "tagline": "Your private AI that sees, understands, and remembers.",
    }


@router.get("/api/status")
def status_route(db: Session = Depends(get_db)) -> dict[str, Any]:
    stats = memory_service.get_stats(db)
    privacy = privacy_service.get_policy(db)

    return {
        "app_name": "SENTINEL",
        "tagline": "Your private AI that sees, understands, and remembers.",
        "phase": "Phase 1 — Foundation",
        "indicators": {
            "ai_engine": {"label": "AI POLICY", "status": "Local AI Policy: Enabled", "tone": "ready"},
            "ai_model": {"label": "AI MODEL", "status": "Not Connected", "tone": "not_connected"},
            "vision": {"label": "VISION", "status": "Not Connected", "tone": "not_connected"},
            "audio": {"label": "AUDIO", "status": "Not Connected", "tone": "not_connected"},
            "memory": {"label": "MEMORY", "status": "Local Storage Ready", "tone": "ready"},
            "privacy": {"label": "PRIVACY", "status": "Local Preference Enforced", "tone": "ready"},
            "network": {"label": "NETWORK", "status": "Not Required for Core Architecture", "tone": "ready"},
            "npu": {"label": "NPU ACCELERATION", "status": "Not Verified", "tone": "not_connected"},
        },
        "privacy_policy": privacy.model_dump(),
        "memory_stats": stats.model_dump(),
        "ai_model_connected": False,
        "npu_verified": False,
    }


# ---------------------------------------------------------------------------
# Privacy Controls (Section 11, 20) - Persisted to SQLite
# ---------------------------------------------------------------------------
@router.get("/api/privacy", response_model=PrivacyPolicy)
def get_privacy_policy(db: Session = Depends(get_db)) -> PrivacyPolicy:
    return privacy_service.get_policy(db)


@router.put("/api/privacy", response_model=PrivacyPolicy)
def update_privacy_policy(update: PrivacyPolicyUpdate, db: Session = Depends(get_db)) -> PrivacyPolicy:
    return privacy_service.update_policy(update, db)


# ---------------------------------------------------------------------------
# Memory (Section 7, 8, 21)
# ---------------------------------------------------------------------------
@router.get("/api/memory", response_model=list[MemoryRead])
def list_memories(
    category: str | None = Query(None, description="Filter category"),
    search: str | None = Query(None, description="Search keyword in title/content"),
    project_id: int | None = Query(None, description="Filter by associated project"),
    db: Session = Depends(get_db),
) -> list[MemoryRead]:
    return memory_service.list_memories(db, category=category, search=search, project_id=project_id)


@router.get("/api/memory/stats", response_model=MemoryStats)
def get_memory_stats(db: Session = Depends(get_db)) -> MemoryStats:
    return memory_service.get_stats(db)


@router.post("/api/memory/search", response_model=MemorySearchResponse)
def search_memories_post(
    req: MemorySearchQuery,
    db: Session = Depends(get_db),
) -> MemorySearchResponse:
    return memory_service.search_memories(db, req)


@router.get("/api/memory/search", response_model=MemorySearchResponse)
def search_memories_get(
    q: str = Query(..., min_length=1, description="Search query string"),
    mode: str = Query("HYBRID", description="SEMANTIC, KEYWORD, or HYBRID"),
    top_k: int = Query(5, ge=1, le=50),
    project_id: int | None = Query(None),
    category: str | None = Query(None),
    source_type: str | None = Query(None),
    include_documents: bool = Query(True),
    db: Session = Depends(get_db),
) -> MemorySearchResponse:
    req = MemorySearchQuery(
        query=q,
        search_mode=mode,
        top_k=top_k,
        project_id=project_id,
        category=category,
        source_type=source_type,
        include_documents=include_documents,
    )
    return memory_service.search_memories(db, req)


@router.post("/api/memory/check-duplicate", response_model=DuplicateCheckResponse)
def check_duplicate_memory(
    req: DuplicateCheckRequest,
    db: Session = Depends(get_db),
) -> DuplicateCheckResponse:
    return memory_service.check_duplicate(db, req)


@router.get("/api/memory/embedding-status", response_model=EmbeddingStatusResponse)
def get_memory_embedding_status(db: Session = Depends(get_db)) -> EmbeddingStatusResponse:
    return memory_service.get_embedding_status(db)


@router.post("/api/memory/embed", response_model=MemoryEmbedResponse)
def embed_text_route(
    req: MemoryEmbedRequest,
) -> MemoryEmbedResponse:
    return memory_service.embed_text(req)


@router.post("/api/memory/reindex", response_model=ReindexResponse)
def reindex_memories(
    force: bool = Query(False, description="Whether to re-embed all items including READY ones"),
    include_documents: bool = Query(True, description="Whether to also reindex document chunks"),
    db: Session = Depends(get_db),
) -> ReindexResponse:
    return memory_service.reindex_memories(db, force=force, include_documents=include_documents)


@router.post("/api/memory", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
def create_memory(memory: MemoryCreate, db: Session = Depends(get_db)) -> MemoryRead:
    return memory_service.create_memory(db, memory)


@router.get("/api/memory/{memory_id}", response_model=MemoryRead)
def get_memory(memory_id: int, db: Session = Depends(get_db)) -> MemoryRead:
    return memory_service.get_memory(db, memory_id)


@router.put("/api/memory/{memory_id}", response_model=MemoryRead)
def update_memory(
    memory_id: int,
    memory: MemoryUpdate,
    db: Session = Depends(get_db),
) -> MemoryRead:
    return memory_service.update_memory(db, memory_id, memory)


@router.delete("/api/memory/{memory_id}")
def delete_memory(memory_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    return memory_service.delete_memory(db, memory_id)


@router.delete("/api/memory")
def delete_all_memories(
    confirm: bool = Query(False, description="Must be true to purge all memories"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required: pass ?confirm=true to delete all stored memories.",
        )
    return memory_service.delete_all_memories(db)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
@router.get("/api/projects", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)) -> list[ProjectRead]:
    return project_service.list_projects(db)


@router.post("/api/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectRead:
    return project_service.create_project(db, payload)


@router.delete("/api/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    return project_service.delete_project(db, project_id)


# ---------------------------------------------------------------------------
# Chat & Multimodal Reasoning (Section 9, 21)
# ---------------------------------------------------------------------------
@router.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatMessageRequest, db: Session = Depends(get_db)) -> ChatResponse:
    return chat_service.process_message(db, payload)


@router.get("/api/chat/conversations", response_model=list[ConversationRead])
def list_conversations(db: Session = Depends(get_db)) -> list[ConversationRead]:
    return chat_service.list_conversations(db)


@router.post("/api/chat/conversations", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)) -> ConversationRead:
    return chat_service.create_conversation(db, payload)


@router.get("/api/chat/conversations/{conversation_id}/messages", response_model=list[ChatMessageRead])
def get_conversation_messages(conversation_id: int, db: Session = Depends(get_db)) -> list[ChatMessageRead]:
    return chat_service.get_messages(db, conversation_id)


@router.get("/api/chat/reasoning-status")
def get_reasoning_status() -> dict[str, Any]:
    from app.ai.reasoning.engine import ReasoningEngine
    return ReasoningEngine.get_instance().get_status()


# ---------------------------------------------------------------------------
# Sentinel Multimodal Orchestrator (Step 7)
# ---------------------------------------------------------------------------
@router.post("/api/sentinel/query", response_model=MultimodalQueryResponse)
def query_sentinel(
    payload: MultimodalQueryRequest,
    db: Session = Depends(get_db),
) -> MultimodalQueryResponse:
    """
    End-to-end multimodal query orchestration across Vision, OCR, Memory, Documents, and Voice.
    Returns grounded synthesis, source citations, and structured UI grounding actions.
    Supports both 'live' and 'demo' execution modes.
    """
    return sentinel_orchestrator.process_query(db, payload)


@router.get("/api/sentinel/demo-fixtures")
def get_sentinel_demo_fixtures() -> dict[str, Any]:
    """
    Returns reproducible, deterministic test fixtures for competition DEMO MODE.
    Clearly labeled DEMO / SIMULATION.
    """
    return {
        "status": "READY",
        "mode": "DEMO / SIMULATION",
        "tracks": [t.model_dump() for t in demo_fixture_service.get_demo_workspace_tracks()],
        "relations": [r.model_dump() for r in demo_fixture_service.get_demo_relations()],
        "memories": demo_fixture_service.get_demo_memories(),
        "documents": demo_fixture_service.get_demo_documents(),
        "evidence": [e.model_dump() for e in demo_fixture_service.get_demo_evidence()],
    }




# ---------------------------------------------------------------------------
# Attachments & Files (Section 23)
# ---------------------------------------------------------------------------
@router.post("/api/files/upload", response_model=AttachmentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    memory_id: int | None = Form(None),
    conversation_id: int | None = Form(None),
    db: Session = Depends(get_db),
) -> AttachmentUploadResponse:
    result = await vision_service.save_uploaded_file(
        file,
        db=db,
        memory_id=memory_id,
        conversation_id=conversation_id,
    )
    return AttachmentUploadResponse(**result)


@router.get("/api/attachments", response_model=list[AttachmentRead])
def list_attachments(
    memory_id: int | None = Query(None),
    conversation_id: int | None = Query(None),
    db: Session = Depends(get_db),
) -> list[AttachmentRead]:
    query = db.query(Attachment)
    if memory_id is not None:
        query = query.filter(Attachment.memory_id == memory_id)
    if conversation_id is not None:
        query = query.filter(Attachment.conversation_id == conversation_id)
    attachments = query.order_by(Attachment.created_at.desc()).all()
    return [AttachmentRead.model_validate(a) for a in attachments]


@router.get("/api/attachments/{file_id}", response_model=AttachmentRead)
def get_attachment(file_id: str, db: Session = Depends(get_db)) -> AttachmentRead:
    att = db.query(Attachment).filter(Attachment.file_id == file_id).first()
    if not att:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attachment '{file_id}' not found.",
        )
    return AttachmentRead.model_validate(att)


# ---------------------------------------------------------------------------
# Vision (Section 6, 21, 24)
# ---------------------------------------------------------------------------
@router.post("/api/vision/analyze", response_model=VisionResult)
def analyze_vision(
    payload: VisionAnalyzeRequest | None = None,
    db: Session = Depends(get_db),
) -> VisionResult:
    result = vision_service.analyze_frame(request=payload, db=db)
    return VisionResult(**result)


@router.post("/api/vision/capture", response_model=FrameCaptureResponse)
def capture_vision(payload: FrameCaptureRequest, db: Session = Depends(get_db)) -> FrameCaptureResponse:
    result = vision_service.capture_frame(payload.model_dump(), db=db)
    return FrameCaptureResponse(**result)


@router.post("/api/vision/upload", response_model=AttachmentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_vision_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> AttachmentUploadResponse:
    result = await vision_service.save_uploaded_file(file, db=db)
    return AttachmentUploadResponse(**result)


@router.get("/api/vision/model/status")
def get_vision_model_status() -> dict[str, Any]:
    from app.ai.vision.inference_engine import inference_engine
    return inference_engine.get_pipeline_status()


@router.post("/api/vision/model/load")
def load_vision_model() -> dict[str, Any]:
    from app.ai.vision.inference_engine import inference_engine
    inference_engine.ensure_loaded()
    return {
        "status": "LOADED",
        "message": "Vision model loaded successfully into memory.",
        **inference_engine.get_pipeline_status(),
    }


@router.post("/api/vision/model/unload")
def unload_vision_model() -> dict[str, Any]:
    from app.ai.vision.inference_engine import inference_engine
    inference_engine.unload()
    return {
        "status": "UNLOADED",
        "message": "Vision model successfully unloaded.",
        **inference_engine.get_pipeline_status(),
    }


@router.post("/api/vision/benchmark", response_model=BenchmarkRecord)
def run_vision_benchmark(
    file_id: str | None = None,
    warmup: int = 3,
    runs: int = 10,
    db: Session = Depends(get_db),
) -> BenchmarkRecord:
    from PIL import Image
    from app.ai.vision.inference_engine import inference_engine
    if file_id:
        att = db.query(Attachment).filter(Attachment.file_id == file_id).first()
        if not att or not os.path.exists(att.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Attachment '{file_id}' not found.",
            )
        img = Image.open(att.file_path)
    else:
        img = Image.new("RGB", (640, 480), color=(180, 180, 180))

    return inference_engine.run_benchmark(img, warmup_runs=warmup, measured_runs=runs)


# ---------------------------------------------------------------------------
# Workspace Tracking & Find It (Step 5)
# ---------------------------------------------------------------------------
@router.post("/api/vision/track", response_model=WorkspaceStateResponse)
def track_workspace_frame(
    payload: WorkspaceTrackRequest,
    db: Session = Depends(get_db),
) -> WorkspaceStateResponse:
    from app.schemas.vision import Detection as VisionDetection
    from app.schemas.ocr import OCRResult as VisionOCRResult
    import time as pytime

    detections: list[VisionDetection] = []
    ocr_results: list[VisionOCRResult] = []

    # If client passed raw detection objects directly
    if payload.detections:
        for d in payload.detections:
            detections.append(VisionDetection.model_validate(d))
    elif payload.image or payload.file_id:
        vis_req = VisionAnalyzeRequest(
            file_id=payload.file_id,
            image=payload.image,
            confidence_threshold=payload.confidence_threshold,
        )
        vis_res = vision_service.analyze_frame(vis_req, db=db)
        for d in vis_res.get("objects", []):
            if isinstance(d, VisionDetection):
                detections.append(d)
            elif isinstance(d, dict):
                detections.append(VisionDetection.model_validate(d))

    if payload.ocr_results:
        for r in payload.ocr_results:
            ocr_results.append(VisionOCRResult.model_validate(r))

    active_tracks, relations = workspace_state.update_workspace(
        detections=detections,
        ocr_results=ocr_results,
        project_id=payload.project_id,
    )

    observations = workspace_state.get_recent_observations()

    return WorkspaceStateResponse(
        status="SUCCESS",
        session_state=workspace_state.session_state.value,
        active_tracks_count=len(active_tracks),
        tracked_objects=active_tracks,
        relations=relations,
        recent_observations=observations,
        timestamp=pytime.time(),
    )


@router.get("/api/workspace/state", response_model=WorkspaceStateResponse)
def get_workspace_state() -> WorkspaceStateResponse:
    import time as pytime
    active_tracks = [
        t for t in workspace_state.tracker.tracks.values()
        if t.visibility_state in (VisibilityState.CURRENT_VISIBLE.value, VisibilityState.RECENTLY_SEEN.value)
    ]
    relations = spatial_engine.compute_relations(active_tracks)
    observations = workspace_state.get_recent_observations()
    return WorkspaceStateResponse(
        status="READY",
        session_state=workspace_state.session_state.value,
        active_tracks_count=len(active_tracks),
        tracked_objects=active_tracks,
        relations=relations,
        recent_observations=observations,
        timestamp=pytime.time(),
    )


@router.post("/api/workspace/find", response_model=FindItResponse)
def find_workspace_object(
    payload: FindItRequest,
) -> FindItResponse:
    return find_it_service.query(
        query_text=payload.query,
        project_id=payload.project_id,
        target_label=payload.target_label,
    )


@router.post("/api/workspace/remember")
def remember_workspace_object(
    payload: RememberObjectRequest,
) -> dict[str, Any]:
    ok = workspace_state.remember_object(
        track_id=payload.track_id,
        user_label=payload.user_label,
        project_id=payload.project_id,
    )
    return {
        "status": "SUCCESS" if ok else "WARNING",
        "message": f"Remembered '{payload.user_label}' for {payload.track_id}." if ok else f"Stored alias '{payload.user_label}' for {payload.track_id}.",
        "track_id": payload.track_id,
        "user_label": payload.user_label,
    }


@router.post("/api/workspace/session")
def update_workspace_session(
    state: str = Query(..., description="ACTIVE, PAUSED, STOPPING, IDLE"),
) -> dict[str, str]:
    try:
        sess_state = TrackingSessionState(state.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session state '{state}'. Valid states: {[s.value for s in TrackingSessionState]}",
        )
    workspace_state.set_session_state(sess_state)
    return {
        "status": "SUCCESS",
        "session_state": sess_state.value,
        "message": f"Workspace session state changed to {sess_state.value}.",
    }


@router.delete("/api/workspace/state")
def clear_workspace_state() -> dict[str, str]:
    workspace_state.reset()
    return {
        "status": "CLEARED",
        "message": "Workspace tracks and spatial observations reset.",
    }


# ---------------------------------------------------------------------------
# Speech Engine & Voice Interaction (Step 6)
# ---------------------------------------------------------------------------
@router.post("/api/speech/transcribe", response_model=SpeechTranscribeResponse)
def transcribe_speech(
    payload: SpeechTranscribeRequest,
    db: Session = Depends(get_db),
) -> SpeechTranscribeResponse:
    """
    Transcribe speech locally using on-device Whisper model.
    Routes transcript to Find It, Workspace Memory, Documents, or Ask SENTINEL.
    Raw audio is never stored or transmitted to the cloud.
    """
    return speech_service.transcribe(payload, db=db)


@router.get("/api/speech/status", response_model=VoiceStatusResponse)
def get_speech_status() -> VoiceStatusResponse:
    """
    Get current speech engine and microphone lifecycle status.
    Truthfully differentiates host CPU execution from Snapdragon target.
    """
    return speech_service.get_status()


@router.post("/api/speech/status")
def set_speech_mic_state(
    state: str = Query(..., description="IDLE, REQUESTING_PERMISSION, READY, RECORDING, PROCESSING, TRANSCRIBED, ERROR"),
) -> VoiceStatusResponse:
    try:
        mstate = MicrophoneState(state.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid microphone state '{state}'. Valid: {[s.value for s in MicrophoneState]}",
        )
    return speech_service.set_microphone_state(mstate)


@router.post("/api/speech/benchmark", response_model=VoiceBenchmarkResult)
def run_speech_benchmark(
    duration: float = Query(3.0, ge=1.0, le=10.0, description="Audio duration in seconds"),
) -> VoiceBenchmarkResult:
    """
    Run local speech benchmark on host CPU.
    Snapdragon NPU status is reported strictly as NOT VERIFIED.
    """
    return speech_service.run_benchmark(duration_sec=duration)


# ---------------------------------------------------------------------------
# OCR & Document Intelligence (Step 9)
# ---------------------------------------------------------------------------
@router.post("/api/ocr/analyze", response_model=OCRResult)
def analyze_ocr(payload: OCRAnalyzeRequest | None = None, db: Session = Depends(get_db)) -> OCRResult:
    try:
        return ocr_service.analyze_image(request=payload, db=db)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"OCR analysis failed: {e}")


@router.get("/api/ocr/status", response_model=OCRStatusResponse)
def get_ocr_status() -> OCRStatusResponse:
    return ocr_service.get_status()


@router.post("/api/ocr/benchmark", response_model=BenchmarkRecord)
def run_ocr_benchmark(
    file_id: str | None = None,
    warmup: int = 2,
    runs: int = 5,
    db: Session = Depends(get_db),
) -> BenchmarkRecord:
    try:
        return ocr_service.run_benchmark(file_id=file_id, warmup=warmup, runs=runs, db=db)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/api/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(payload: DocumentCreateRequest, db: Session = Depends(get_db)) -> DocumentResponse:
    try:
        return document_service.ingest_document(file_id=payload.file_id, force_ocr=payload.force_ocr, db=db)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Document ingestion failed: {e}")


@router.get("/api/documents", response_model=list[DocumentResponse])
def list_documents(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[DocumentResponse]:
    return document_service.list_documents(db=db, limit=limit, offset=offset)


@router.get("/api/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, db: Session = Depends(get_db)) -> DocumentResponse:
    try:
        return document_service.get_document(document_id=document_id, db=db, include_pages=True)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/api/documents/{document_id}/pages", response_model=list[DocumentPageResponse])
def get_document_pages(document_id: str, db: Session = Depends(get_db)) -> list[DocumentPageResponse]:
    try:
        return document_service.get_document_pages(document_id=document_id, db=db)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/api/documents/{document_id}/text")
def get_document_text(document_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        return document_service.get_document_text(document_id=document_id, db=db)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/api/documents/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        return document_service.delete_document(document_id=document_id, db=db)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/api/search/documents", response_model=DocumentSearchResponse)
def search_documents(q: str = Query(..., min_length=1), db: Session = Depends(get_db)) -> DocumentSearchResponse:
    return document_service.search_documents(query=q, db=db)


# ---------------------------------------------------------------------------
# AI Lab & Hardware / Benchmarks (Section 10, 18, 25)
# ---------------------------------------------------------------------------
@router.get("/api/models/status")
def models_status() -> dict[str, Any]:
    return model_manager.report_model_status()


@router.post("/api/models/{model_name}/load")
def load_model(model_name: str) -> dict[str, Any]:
    return model_manager.load_model(model_name)


@router.post("/api/models/{model_name}/unload")
def unload_model(model_name: str) -> dict[str, Any]:
    return model_manager.unload_model(model_name)


@router.get("/api/benchmarks", response_model=BenchmarkSummary)
def get_benchmarks() -> BenchmarkSummary:
    return benchmark_manager.get_summary()


@router.post("/api/benchmarks/run", response_model=BenchmarkRecord)
def run_benchmark() -> BenchmarkRecord:
    return benchmark_manager.run_storage_baseline()


@router.get("/api/system/hardware", response_model=HardwareDiagnosticsResponse)
def get_hardware_info() -> HardwareDiagnosticsResponse:
    return hardware_diagnostics.get_diagnostics()


@router.get("/api/system/runtime", response_model=RuntimeDiagnosticsResponse)
def get_runtime_info() -> RuntimeDiagnosticsResponse:
    return runtime_diagnostics.get_diagnostics()


@router.get("/api/system/diagnostics", response_model=FullDiagnosticsResponse)
def get_full_diagnostics() -> FullDiagnosticsResponse:
    hw = hardware_diagnostics.get_diagnostics()
    rt = runtime_diagnostics.get_diagnostics()
    tp = hardware_diagnostics.load_target_profile()
    summary = (
        f"Host: {hw.processor_name} ({hw.system_architecture}) | "
        f"Snapdragon: {'Yes' if hw.snapdragon_detected else 'No (Development Host)'} | "
        f"NPU: {'Detected' if hw.npu_detected else 'Not Detected'} (Verification: NOT VERIFIED) | "
        f"Runtime: ONNX Runtime v{rt.onnxruntime_version or 'Not Installed'} | "
        f"Provider: {rt.selected_provider}"
    )
    return FullDiagnosticsResponse(
        hardware=hw,
        runtime=rt,
        target_profile=tp,
        summary=summary,
    )


@router.get("/api/system/environment-report")
def get_environment_report_endpoint() -> dict[str, str]:
    return {"report": generate_environment_report()}


@router.get("/api/models/candidates", response_model=list[ModelCandidateRecord])
def get_model_candidates() -> list[ModelCandidateRecord]:
    return model_registry.list_candidates()


@router.get("/api/models/selection", response_model=ModelSelectionResponse)
def get_model_selection() -> ModelSelectionResponse:
    return model_selector.select_first_candidate()
