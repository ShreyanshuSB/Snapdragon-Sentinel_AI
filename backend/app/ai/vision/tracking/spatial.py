from __future__ import annotations

import math
from typing import Sequence
from app.ai.vision.tracking.models import SpatialRegion, SpatialRelation, TrackedObject
from app.schemas.vision import BoundingBox


def compute_iou(box_a: BoundingBox, box_b: BoundingBox) -> float:
    """Compute Intersection-over-Union between two normalized bounding boxes."""
    x_a1, y_a1 = box_a.x, box_a.y
    x_a2, y_a2 = box_a.x + box_a.width, box_a.y + box_a.height

    x_b1, y_b1 = box_b.x, box_b.y
    x_b2, y_b2 = box_b.x + box_b.width, box_b.y + box_b.height

    inter_x1 = max(x_a1, x_b1)
    inter_y1 = max(y_a1, y_b1)
    inter_x2 = min(x_a2, x_b2)
    inter_y2 = min(y_a2, y_b2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area_a = max(0.0, box_a.width * box_a.height)
    area_b = max(0.0, box_b.width * box_b.height)
    union_area = area_a + area_b - inter_area

    if union_area <= 1e-7:
        return 0.0
    return inter_area / union_area


def compute_centroid_distance(cx1: float, cy1: float, cx2: float, cy2: float) -> float:
    """Euclidean distance between two normalized 2D centroids."""
    return math.sqrt((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2)


def get_spatial_region(center_x: float, center_y: float) -> SpatialRegion:
    """
    Classify a normalized 2D centroid into one of 9 discrete workspace zones:
    x in [0.0, 0.35) -> left, [0.35, 0.65] -> center, (0.65, 1.0] -> right
    y in [0.0, 0.35) -> top, [0.35, 0.65] -> center, (0.65, 1.0] -> bottom
    """
    # Clamp coordinates to [0.0, 1.0]
    cx = max(0.0, min(1.0, center_x))
    cy = max(0.0, min(1.0, center_y))

    if cy < 0.35:
        if cx < 0.35:
            return SpatialRegion.TOP_LEFT
        elif cx > 0.65:
            return SpatialRegion.TOP_RIGHT
        else:
            return SpatialRegion.TOP_CENTER
    elif cy > 0.65:
        if cx < 0.35:
            return SpatialRegion.BOTTOM_LEFT
        elif cx > 0.65:
            return SpatialRegion.BOTTOM_RIGHT
        else:
            return SpatialRegion.BOTTOM_CENTER
    else:
        if cx < 0.35:
            return SpatialRegion.CENTER_LEFT
        elif cx > 0.65:
            return SpatialRegion.CENTER_RIGHT
        else:
            return SpatialRegion.CENTER


class SpatialReasoningEngine:
    """
    Deterministic geometry engine computing spatial zones and relative positions
    between detected workspace tracks without relying on an LLM.
    """

    def __init__(
        self,
        horizontal_threshold: float = 0.08,
        vertical_threshold: float = 0.08,
        near_distance_threshold: float = 0.35,
        overlap_iou_threshold: float = 0.04,
    ) -> None:
        self.horizontal_threshold = horizontal_threshold
        self.vertical_threshold = vertical_threshold
        self.near_distance_threshold = near_distance_threshold
        self.overlap_iou_threshold = overlap_iou_threshold

    def classify_region(self, center_x: float, center_y: float) -> str:
        return get_spatial_region(center_x, center_y).value

    def compute_relations(self, tracks: Sequence[TrackedObject]) -> list[SpatialRelation]:
        """
        Compute deterministic geometric relations for all pairs of active tracks.
        """
        relations: list[SpatialRelation] = []
        n = len(tracks)
        if n < 2:
            return relations

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                a = tracks[i]
                b = tracks[j]

                label_a = a.user_label or a.class_name
                label_b = b.user_label or b.class_name

                dx = a.center_x - b.center_x
                dy = a.center_y - b.center_y
                dist = compute_centroid_distance(a.center_x, a.center_y, b.center_x, b.center_y)
                iou = compute_iou(a.smoothed_bbox, b.smoothed_bbox)

                # Overlap
                if iou >= self.overlap_iou_threshold:
                    relations.append(
                        SpatialRelation(
                            source_track_id=a.track_id,
                            relation_type="overlaps",
                            target_track_id=b.track_id,
                            source_label=label_a,
                            target_label=label_b,
                            description=f"{label_a} overlaps {label_b}",
                            confidence=round(min(1.0, iou * 5.0), 2),
                        )
                    )

                # Horizontal relationships
                if dx < -self.horizontal_threshold:
                    relations.append(
                        SpatialRelation(
                            source_track_id=a.track_id,
                            relation_type="left_of",
                            target_track_id=b.track_id,
                            source_label=label_a,
                            target_label=label_b,
                            description=f"{label_a} is left of {label_b}",
                            confidence=round(min(1.0, abs(dx) * 2.0), 2),
                        )
                    )
                elif dx > self.horizontal_threshold:
                    relations.append(
                        SpatialRelation(
                            source_track_id=a.track_id,
                            relation_type="right_of",
                            target_track_id=b.track_id,
                            source_label=label_a,
                            target_label=label_b,
                            description=f"{label_a} is right of {label_b}",
                            confidence=round(min(1.0, abs(dx) * 2.0), 2),
                        )
                    )

                # Vertical relationships
                if dy < -self.vertical_threshold:
                    relations.append(
                        SpatialRelation(
                            source_track_id=a.track_id,
                            relation_type="above",
                            target_track_id=b.track_id,
                            source_label=label_a,
                            target_label=label_b,
                            description=f"{label_a} is above {label_b}",
                            confidence=round(min(1.0, abs(dy) * 2.0), 2),
                        )
                    )
                elif dy > self.vertical_threshold:
                    relations.append(
                        SpatialRelation(
                            source_track_id=a.track_id,
                            relation_type="below",
                            target_track_id=b.track_id,
                            source_label=label_a,
                            target_label=label_b,
                            description=f"{label_a} is below {label_b}",
                            confidence=round(min(1.0, abs(dy) * 2.0), 2),
                        )
                    )

                # Nearness
                if dist <= self.near_distance_threshold:
                    relations.append(
                        SpatialRelation(
                            source_track_id=a.track_id,
                            relation_type="near",
                            target_track_id=b.track_id,
                            source_label=label_a,
                            target_label=label_b,
                            description=f"{label_a} is near {label_b}",
                            confidence=round(max(0.1, 1.0 - (dist / self.near_distance_threshold)), 2),
                        )
                    )

        return relations


spatial_engine = SpatialReasoningEngine()
