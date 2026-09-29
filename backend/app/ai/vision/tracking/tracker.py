from __future__ import annotations

import time
from typing import Sequence
from app.ai.vision.tracking.models import (
    SpatialRegion,
    TrackedObject,
    VisibilityState,
)
from app.ai.vision.tracking.spatial import (
    compute_centroid_distance,
    compute_iou,
    get_spatial_region,
)
from app.schemas.vision import BoundingBox, Detection


class ObjectTracker:
    """
    Lightweight, deterministic 2D object tracker for desktop workspaces.
    Uses multi-stage matching (IoU + centroid proximity), EMA temporal smoothing,
    velocity estimation, and timeout pruning without requiring heavy neural networks.
    """

    def __init__(
        self,
        iou_threshold: float = 0.25,
        centroid_distance_threshold: float = 0.25,
        max_missed_frames: int = 15,
        min_confidence: float = 0.20,
        smoothing_factor: float = 0.65,  # Weight for new detection in EMA
        stale_timeout_seconds: float = 10.0,
        expired_timeout_seconds: float = 60.0,
    ) -> None:
        self.iou_threshold = iou_threshold
        self.centroid_distance_threshold = centroid_distance_threshold
        self.max_missed_frames = max_missed_frames
        self.min_confidence = min_confidence
        self.smoothing_factor = smoothing_factor
        self.stale_timeout_seconds = stale_timeout_seconds
        self.expired_timeout_seconds = expired_timeout_seconds

        self._tracks: dict[str, TrackedObject] = {}
        self._next_id: int = 1
        self._last_update_time: float = time.time()

    @property
    def tracks(self) -> dict[str, TrackedObject]:
        return self._tracks

    def get_active_tracks(self) -> list[TrackedObject]:
        return [t for t in self._tracks.values() if t.visibility_state == VisibilityState.CURRENT_VISIBLE]

    def reset(self) -> None:
        """Clear all active tracks and reset counter."""
        self._tracks.clear()
        self._next_id = 1
        self._last_update_time = time.time()

    def update(
        self,
        detections: Sequence[Detection],
        timestamp: float | None = None,
        project_id: str | None = None,
    ) -> list[TrackedObject]:
        """
        Process a new frame's detections and update tracked objects.
        Returns the list of currently visible/active tracked objects.
        """
        current_time = timestamp if timestamp is not None else time.time()
        dt = max(0.01, current_time - self._last_update_time)
        self._last_update_time = current_time

        # Filter detections by minimum confidence
        valid_detections = [d for d in detections if d.confidence >= self.min_confidence]

        matched_tracks: set[str] = set()
        matched_detections: set[int] = set()

        existing_track_ids = list(self._tracks.keys())

        # Stage 1: Match by class name and IoU
        for d_idx, det in enumerate(valid_detections):
            best_iou = -1.0
            best_track_id: str | None = None

            for t_id in existing_track_ids:
                if t_id in matched_tracks:
                    continue
                track = self._tracks[t_id]
                # Same class matching prioritized
                if track.class_name.lower() == det.label.lower():
                    iou = compute_iou(track.smoothed_bbox, det.bbox)
                    if iou > self.iou_threshold and iou > best_iou:
                        best_iou = iou
                        best_track_id = t_id

            if best_track_id is not None:
                matched_tracks.add(best_track_id)
                matched_detections.add(d_idx)
                self._update_track(best_track_id, det, current_time, dt, project_id)

        # Stage 2: Match remaining detections by centroid proximity (same class)
        for d_idx, det in enumerate(valid_detections):
            if d_idx in matched_detections:
                continue

            det_cx = det.bbox.x + det.bbox.width / 2.0
            det_cy = det.bbox.y + det.bbox.height / 2.0

            best_dist = float("inf")
            best_track_id: str | None = None

            for t_id in existing_track_ids:
                if t_id in matched_tracks:
                    continue
                track = self._tracks[t_id]
                if track.class_name.lower() == det.label.lower():
                    dist = compute_centroid_distance(track.center_x, track.center_y, det_cx, det_cy)
                    if dist < self.centroid_distance_threshold and dist < best_dist:
                        best_dist = dist
                        best_track_id = t_id

            if best_track_id is not None:
                matched_tracks.add(best_track_id)
                matched_detections.add(d_idx)
                self._update_track(best_track_id, det, current_time, dt, project_id)

        # Stage 3: Unmatched detections spawn new tracks
        for d_idx, det in enumerate(valid_detections):
            if d_idx not in matched_detections:
                self._create_track(det, current_time, project_id)

        # Stage 4: Handle tracks not matched in this frame
        for t_id in existing_track_ids:
            if t_id not in matched_tracks:
                track = self._tracks[t_id]
                track.consecutive_misses += 1
                age = current_time - track.last_seen_timestamp

                # Update visibility state
                if age <= 3.0 and track.consecutive_misses <= 5:
                    track.visibility_state = VisibilityState.RECENTLY_SEEN.value
                elif age <= self.stale_timeout_seconds:
                    track.visibility_state = VisibilityState.STALE.value
                else:
                    track.visibility_state = VisibilityState.EXPIRED.value

                # Update stability score
                total_frames = track.frames_seen + track.consecutive_misses
                track.stability_score = round(track.frames_seen / max(1, total_frames), 3)

        # Stage 5: Prune completely expired tracks beyond timeout or max misses
        to_delete: list[str] = []
        for t_id, track in self._tracks.items():
            age = current_time - track.last_seen_timestamp
            if (
                track.consecutive_misses > self.max_missed_frames
                and age > self.stale_timeout_seconds
            ) or age > self.expired_timeout_seconds:
                to_delete.append(t_id)

        for t_id in to_delete:
            del self._tracks[t_id]

        # Return active / recently seen objects
        return [
            t
            for t in self._tracks.values()
            if t.visibility_state in (VisibilityState.CURRENT_VISIBLE.value, VisibilityState.RECENTLY_SEEN.value)
        ]

    def _create_track(self, det: Detection, current_time: float, project_id: str | None) -> str:
        """Instantiate a new tracked entity."""
        track_id = f"track_{self._next_id:03d}"
        self._next_id += 1

        cx = det.bbox.x + det.bbox.width / 2.0
        cy = det.bbox.y + det.bbox.height / 2.0
        region_str = get_spatial_region(cx, cy).value

        # Initial smoothed bbox is identical to raw
        smoothed = BoundingBox(
            x=round(det.bbox.x, 4),
            y=round(det.bbox.y, 4),
            width=round(det.bbox.width, 4),
            height=round(det.bbox.height, 4),
            x_min=round(det.bbox.x_min, 4),
            y_min=round(det.bbox.y_min, 4),
            x_max=round(det.bbox.x_max, 4),
            y_max=round(det.bbox.y_max, 4),
        )

        track = TrackedObject(
            track_id=track_id,
            class_id=det.class_id,
            class_name=det.label,
            confidence=round(det.confidence, 4),
            raw_bbox=det.bbox,
            smoothed_bbox=smoothed,
            center_x=round(cx, 4),
            center_y=round(cy, 4),
            width=round(det.bbox.width, 4),
            height=round(det.bbox.height, 4),
            velocity_x=0.0,
            velocity_y=0.0,
            first_seen_timestamp=current_time,
            last_seen_timestamp=current_time,
            frames_seen=1,
            consecutive_misses=0,
            visibility_state=VisibilityState.CURRENT_VISIBLE.value,
            region=region_str,
            stability_score=1.0,
            project_id=project_id,
        )

        self._tracks[track_id] = track
        return track_id

    def _update_track(
        self,
        track_id: str,
        det: Detection,
        current_time: float,
        dt: float,
        project_id: str | None,
    ) -> None:
        """Update existing track with new detection and apply EMA smoothing."""
        track = self._tracks[track_id]
        alpha = self.smoothing_factor

        # New raw values
        new_x = det.bbox.x
        new_y = det.bbox.y
        new_w = det.bbox.width
        new_h = det.bbox.height
        new_cx = new_x + new_w / 2.0
        new_cy = new_y + new_h / 2.0

        # Velocity estimation
        if dt > 0.001:
            track.velocity_x = round((new_cx - track.center_x) / dt, 4)
            track.velocity_y = round((new_cy - track.center_y) / dt, 4)

        # EMA smoothing: smoothed = alpha * new + (1 - alpha) * old
        old_sm = track.smoothed_bbox
        sm_x = round(alpha * new_x + (1.0 - alpha) * old_sm.x, 4)
        sm_y = round(alpha * new_y + (1.0 - alpha) * old_sm.y, 4)
        sm_w = round(alpha * new_w + (1.0 - alpha) * old_sm.width, 4)
        sm_h = round(alpha * new_h + (1.0 - alpha) * old_sm.height, 4)

        track.raw_bbox = det.bbox
        track.smoothed_bbox = BoundingBox(
            x=sm_x,
            y=sm_y,
            width=sm_w,
            height=sm_h,
            x_min=sm_x,
            y_min=sm_y,
            x_max=round(sm_x + sm_w, 4),
            y_max=round(sm_y + sm_h, 4),
        )

        track.center_x = round(sm_x + sm_w / 2.0, 4)
        track.center_y = round(sm_y + sm_h / 2.0, 4)
        track.width = sm_w
        track.height = sm_h
        track.confidence = round(alpha * det.confidence + (1.0 - alpha) * track.confidence, 4)
        track.last_seen_timestamp = current_time
        track.frames_seen += 1
        track.consecutive_misses = 0
        track.visibility_state = VisibilityState.CURRENT_VISIBLE.value
        track.region = get_spatial_region(track.center_x, track.center_y).value

        total_frames = track.frames_seen + track.consecutive_misses
        track.stability_score = round(track.frames_seen / max(1, total_frames), 3)

        if project_id:
            track.project_id = project_id
