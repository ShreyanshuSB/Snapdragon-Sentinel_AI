from __future__ import annotations

import time
from typing import Any, Sequence
from app.ai.vision.tracking.models import (
    SpatialRelation,
    TrackedObject,
    TrackingSessionState,
    VisibilityState,
    WorkspaceObservation,
)
from app.ai.vision.tracking.spatial import (
    compute_centroid_distance,
    compute_iou,
    spatial_engine,
)
from app.ai.vision.tracking.tracker import ObjectTracker
from app.schemas.vision import BoundingBox, Detection, OCRResult


# Common synonyms / aliases for desk objects
OBJECT_ALIASES: dict[str, list[str]] = {
    "bottle": ["water bottle", "drink", "flask", "thermos", "container"],
    "cup": ["mug", "coffee cup", "tea cup", "glass"],
    "cell phone": ["phone", "smartphone", "mobile", "mobile phone", "iphone", "android"],
    "laptop": ["computer", "notebook", "pc", "macbook", "workstation"],
    "mouse": ["computer mouse", "trackpad", "pointer"],
    "keyboard": ["typing board", "mechanical keyboard", "keypad"],
    "book": ["notebook", "textbook", "manual", "paper", "pad"],
    "pen": ["pencil", "marker", "stylus", "highlighter"],
    "scissors": ["shears", "cutter"],
    "backpack": ["bag", "rucksack", "knapsack"],
    "chair": ["desk chair", "office chair", "seat"],
}


class WorkspaceState:
    """
    Manages real-time spatial memory and observation history for the workspace.
    Maintains active object tracks, historical spatial observations with TTL,
    user-remembered labels, OCR text associations, and deterministic relationships.
    """

    def __init__(
        self,
        recently_seen_ttl: float = 15.0,
        stale_ttl: float = 60.0,
        max_observations: int = 50,
    ) -> None:
        self.recently_seen_ttl = recently_seen_ttl
        self.stale_ttl = stale_ttl
        self.max_observations = max_observations

        self.tracker = ObjectTracker()
        self.session_state = TrackingSessionState.IDLE
        self._remembered_labels: dict[str, str] = {}  # track_id -> user_label
        self._observations: dict[str, WorkspaceObservation] = {}  # track_id -> WorkspaceObservation
        self._last_active_time = time.time()

    def set_session_state(self, state: TrackingSessionState) -> None:
        self.session_state = state
        if state == TrackingSessionState.STOPPING or state == TrackingSessionState.IDLE:
            # Privacy: Clear active tracking on stop
            self.tracker.reset()
            self._observations.clear()
            self._remembered_labels.clear()

    def reset(self) -> None:
        """Clear all tracks and observations."""
        self.tracker.reset()
        self._observations.clear()
        self._remembered_labels.clear()
        self.session_state = TrackingSessionState.IDLE

    def get_active_tracks(self) -> list[TrackedObject]:
        """Return currently active tracks from tracker."""
        return self.tracker.get_active_tracks()

    def update_workspace(
        self,
        detections: Sequence[Detection],
        ocr_results: Sequence[OCRResult] | None = None,
        timestamp: float | None = None,
        project_id: str | None = None,
    ) -> tuple[list[TrackedObject], list[SpatialRelation]]:
        """
        Ingest new detection frame and optional OCR text.
        Updates tracker, associates OCR, computes spatial relations, and refreshes observations.
        """
        now = timestamp if timestamp is not None else time.time()
        self._last_active_time = now

        if self.session_state == TrackingSessionState.IDLE:
            self.session_state = TrackingSessionState.ACTIVE

        # 1. Update tracks
        active_tracks = self.tracker.update(detections, timestamp=now, project_id=project_id)

        # 2. Re-apply remembered user labels
        for track in active_tracks:
            if track.track_id in self._remembered_labels:
                track.user_label = self._remembered_labels[track.track_id]

        # 3. Associate OCR text if provided
        if ocr_results:
            self.associate_ocr_to_tracks(active_tracks, ocr_results)

        # 4. Compute deterministic spatial relations
        relations = spatial_engine.compute_relations(active_tracks)

        # 5. Refresh spatial observations cache
        relation_descriptions = [r.description for r in relations]
        for track in active_tracks:
            # Extract relevant relations mentioning this track
            t_label = track.user_label or track.class_name
            t_relations = [
                r.description for r in relations
                if r.source_track_id == track.track_id or r.target_track_id == track.track_id
            ]

            aliases = OBJECT_ALIASES.get(track.class_name.lower(), [])

            obs = WorkspaceObservation(
                track_id=track.track_id,
                object_label=track.class_name,
                user_label=track.user_label,
                aliases=aliases,
                confidence=track.confidence,
                last_seen_timestamp=track.last_seen_timestamp,
                last_seen_bbox=track.smoothed_bbox,
                normalized_position={"x": track.center_x, "y": track.center_y},
                region=track.region,
                visibility_state=track.visibility_state,
                source="camera",
                project_id=track.project_id,
                ocr_associations=track.ocr_associations,
                relations=t_relations,
            )
            self._observations[track.track_id] = obs

        # Prune expired observations
        self._prune_observations(now)

        return active_tracks, relations

    def associate_ocr_to_tracks(
        self,
        tracks: Sequence[TrackedObject],
        ocr_results: Sequence[OCRResult],
        max_distance: float = 0.20,
    ) -> None:
        """
        Geometrically associate OCR text blocks with nearby or contained detected objects.
        """
        if not tracks or not ocr_results:
            return

        for track in tracks:
            associated_texts: list[str] = []
            for ocr in ocr_results:
                if not ocr.bbox:
                    continue
                ocr_cx = ocr.bbox.x + ocr.bbox.width / 2.0
                ocr_cy = ocr.bbox.y + ocr.bbox.height / 2.0

                # Check if OCR center is inside the object's smoothed bbox
                b = track.smoothed_bbox
                inside = (b.x <= ocr_cx <= b.x + b.width) and (b.y <= ocr_cy <= b.y + b.height)
                dist = compute_centroid_distance(track.center_x, track.center_y, ocr_cx, ocr_cy)

                if inside:
                    associated_texts.append(ocr.text.strip())
                    track.ocr_association_conf = max(track.ocr_association_conf, 0.90)
                elif dist <= max_distance:
                    associated_texts.append(ocr.text.strip())
                    track.ocr_association_conf = max(track.ocr_association_conf, round(1.0 - (dist / max_distance), 2))

            if associated_texts:
                # Deduplicate while preserving order
                seen = set()
                unique_texts = []
                for t in associated_texts:
                    if t and t not in seen:
                        seen.add(t)
                        unique_texts.append(t)
                track.ocr_associations = unique_texts

    def remember_object(self, track_id: str, user_label: str, project_id: str | None = None) -> bool:
        """
        Bind a custom user label to a visible or recent track (e.g. 'my water bottle').
        """
        self._remembered_labels[track_id] = user_label.strip()

        # Update in tracker if currently active
        if track_id in self.tracker.tracks:
            track = self.tracker.tracks[track_id]
            track.user_label = user_label.strip()
            if project_id:
                track.project_id = project_id

        # Update in observations if present
        if track_id in self._observations:
            obs = self._observations[track_id]
            obs.user_label = user_label.strip()
            if project_id:
                obs.project_id = project_id
            return True

        return track_id in self.tracker.tracks

    def get_recent_observations(self, current_time: float | None = None) -> list[WorkspaceObservation]:
        """Get all observations within recent/stale TTL windows."""
        now = current_time if current_time is not None else time.time()
        self._prune_observations(now)
        return list(self._observations.values())

    def _prune_observations(self, now: float) -> None:
        """Update visibility states and prune observations older than stale_ttl."""
        to_remove: list[str] = []
        for t_id, obs in self._observations.items():
            age = now - obs.last_seen_timestamp

            # Check if tracker still considers it active
            is_active_in_tracker = (
                t_id in self.tracker.tracks
                and self.tracker.tracks[t_id].visibility_state == VisibilityState.CURRENT_VISIBLE.value
            )

            if is_active_in_tracker and age <= 3.0:
                obs.visibility_state = VisibilityState.CURRENT_VISIBLE.value
            elif age <= self.recently_seen_ttl:
                obs.visibility_state = VisibilityState.RECENTLY_SEEN.value
            elif age <= self.stale_ttl:
                obs.visibility_state = VisibilityState.STALE.value
            else:
                obs.visibility_state = VisibilityState.EXPIRED.value
                to_remove.append(t_id)

        for t_id in to_remove:
            del self._observations[t_id]


workspace_state = WorkspaceState()
