from __future__ import annotations

import time
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

from app.schemas.vision import BoundingBox


class TrackingSessionState(str, Enum):
    IDLE = "IDLE"
    STARTING = "STARTING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    ERROR = "ERROR"


class VisibilityState(str, Enum):
    CURRENT_VISIBLE = "CURRENT_VISIBLE"
    RECENTLY_SEEN = "RECENTLY_SEEN"
    STALE = "STALE"
    EXPIRED = "EXPIRED"


class MatchType(str, Enum):
    CURRENT_VISIBLE = "CURRENT_VISIBLE"
    RECENTLY_SEEN = "RECENTLY_SEEN"
    STALE = "STALE"
    NOT_FOUND = "NOT_FOUND"
    AMBIGUOUS = "AMBIGUOUS"


class SpatialRegion(str, Enum):
    TOP_LEFT = "top-left"
    TOP_CENTER = "top-center"
    TOP_RIGHT = "top-right"
    CENTER_LEFT = "center-left"
    CENTER = "center"
    CENTER_RIGHT = "center-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_CENTER = "bottom-center"
    BOTTOM_RIGHT = "bottom-right"


class TrackedObject(BaseModel):
    track_id: str = Field(..., description="Unique temporary tracking identifier (e.g. track_001)")
    class_id: int = Field(..., description="Model class ID")
    class_name: str = Field(..., description="Human-readable object class name")
    confidence: float = Field(..., description="Detection confidence [0.0 - 1.0]")
    raw_bbox: BoundingBox = Field(..., description="Unsmoothed bounding box from latest detection")
    smoothed_bbox: BoundingBox = Field(..., description="Temporally smoothed bounding box")
    center_x: float = Field(..., description="Normalized centroid X [0.0 - 1.0]")
    center_y: float = Field(..., description="Normalized centroid Y [0.0 - 1.0]")
    width: float = Field(..., description="Normalized width [0.0 - 1.0]")
    height: float = Field(..., description="Normalized height [0.0 - 1.0]")
    velocity_x: float = Field(default=0.0, description="Estimated centroid horizontal velocity (units/sec)")
    velocity_y: float = Field(default=0.0, description="Estimated centroid vertical velocity (units/sec)")
    first_seen_timestamp: float = Field(default_factory=time.time, description="Timestamp when track was initialized")
    last_seen_timestamp: float = Field(default_factory=time.time, description="Timestamp when track was last detected")
    frames_seen: int = Field(default=1, description="Total number of frames this object was detected")
    consecutive_misses: int = Field(default=0, description="Consecutive frames where detection was missed")
    visibility_state: str = Field(default=VisibilityState.CURRENT_VISIBLE.value, description="Visibility status")
    region: str = Field(default=SpatialRegion.CENTER.value, description="Current workspace spatial region")
    user_label: str | None = Field(default=None, description="Optional user-assigned name (e.g. 'my water bottle')")
    ocr_associations: list[str] = Field(default_factory=list, description="Text extracted nearby or on this object")
    ocr_association_conf: float = Field(default=0.0, description="Confidence of OCR association [0.0 - 1.0]")
    stability_score: float = Field(default=1.0, description="Temporal stability metric [0.0 - 1.0]")
    project_id: str | None = Field(default=None, description="Optional active project filter context")


class SpatialRelation(BaseModel):
    source_track_id: str
    relation_type: str = Field(..., description="left_of, right_of, above, below, near, overlaps")
    target_track_id: str
    source_label: str
    target_label: str
    description: str
    confidence: float = 1.0


class WorkspaceObservation(BaseModel):
    track_id: str
    object_label: str
    user_label: str | None = None
    aliases: list[str] = Field(default_factory=list)
    confidence: float
    last_seen_timestamp: float
    last_seen_bbox: BoundingBox
    normalized_position: dict[str, float]
    region: str
    visibility_state: str
    source: str = "camera"
    project_id: str | None = None
    ocr_associations: list[str] = Field(default_factory=list)
    relations: list[str] = Field(default_factory=list)


class FindItCandidate(BaseModel):
    track_id: str
    object: str
    user_label: str | None = None
    confidence: float
    region: str
    normalized_position: dict[str, float]
    last_seen: str
    age_seconds: float
    relations: list[str] = Field(default_factory=list)
    bbox: BoundingBox


class FindItResponse(BaseModel):
    found: bool
    match_type: str = Field(..., description="CURRENT_VISIBLE, RECENTLY_SEEN, STALE, NOT_FOUND, AMBIGUOUS")
    object: str
    track_id: str | None = None
    confidence: float | None = None
    region: str | None = None
    normalized_position: dict[str, float] | None = None
    last_seen: str | None = None
    age_seconds: float | None = None
    relations: list[str] = Field(default_factory=list)
    candidates: list[FindItCandidate] = Field(default_factory=list)
    message: str
    grounding_box: BoundingBox | None = None


class RememberObjectRequest(BaseModel):
    track_id: str = Field(..., description="Track ID to remember")
    user_label: str = Field(..., description="Human label, e.g. 'my water bottle'")
    project_id: str | None = Field(default=None, description="Optional project context")


class FindItRequest(BaseModel):
    query: str = Field(..., description="Natural language search query, e.g. 'Where is my bottle?'")
    project_id: str | None = Field(default=None, description="Optional project scope filter")
    target_label: str | None = Field(default=None, description="Explicit target label if known")


class WorkspaceTrackRequest(BaseModel):
    image: str | None = Field(default=None, description="Base64 frame if requesting detection + tracking")
    file_id: str | None = Field(default=None, description="File ID if running on stored frame")
    detections: list[dict[str, Any]] | None = Field(default=None, description="Pre-computed detections if available")
    ocr_results: list[dict[str, Any]] | None = Field(default=None, description="Pre-computed OCR results")
    project_id: str | None = Field(default=None, description="Active project context")
    confidence_threshold: float = Field(default=0.25, ge=0.01, le=1.0)


class WorkspaceStateResponse(BaseModel):
    status: str = "READY"
    session_state: str = TrackingSessionState.IDLE.value
    active_tracks_count: int = 0
    tracked_objects: list[TrackedObject] = Field(default_factory=list)
    relations: list[SpatialRelation] = Field(default_factory=list)
    recent_observations: list[WorkspaceObservation] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)
