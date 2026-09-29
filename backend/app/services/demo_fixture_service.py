from __future__ import annotations

from typing import Any
from app.ai.vision.tracking.models import (
    BoundingBox,
    SpatialRelation,
    TrackedObject,
    VisibilityState,
    WorkspaceObservation,
)
from app.schemas.orchestrator import EvidenceCategory, EvidenceItem


class DemoFixtureService:
    """
    Provides reproducible, deterministic test fixtures for competition DEMO MODE.
    Clearly and transparently tagged as DEMO / SIMULATION.
    Never pretends simulated fixtures are real hardware sensor output.
    """

    DEMO_TAG = "DEMO / SIMULATION"

    @classmethod
    def get_demo_workspace_tracks(cls) -> list[TrackedObject]:
        """Deterministic desk objects representing a typical developer desk."""
        return [
            TrackedObject(
                track_id="track_001",
                class_id=39,
                class_name="bottle",
                confidence=0.94,
                raw_bbox=BoundingBox(ymin=0.25, xmin=0.60, ymax=0.72, xmax=0.82),
                smoothed_bbox=BoundingBox(ymin=0.25, xmin=0.60, ymax=0.72, xmax=0.82),
                center_x=0.71,
                center_y=0.485,
                width=0.22,
                height=0.47,
                first_seen_timestamp=1727650000.0,
                last_seen_timestamp=1727650030.0,
                frames_seen=60,
                visibility_state=VisibilityState.CURRENT_VISIBLE,
                region="center_right",
                user_label="water bottle",
                stability_score=0.95,
            ),
            TrackedObject(
                track_id="track_002",
                class_id=63,
                class_name="laptop",
                confidence=0.97,
                raw_bbox=BoundingBox(ymin=0.15, xmin=0.20, ymax=0.80, xmax=0.60),
                smoothed_bbox=BoundingBox(ymin=0.15, xmin=0.20, ymax=0.80, xmax=0.60),
                center_x=0.40,
                center_y=0.475,
                width=0.40,
                height=0.65,
                first_seen_timestamp=1727650000.0,
                last_seen_timestamp=1727650030.0,
                frames_seen=60,
                visibility_state=VisibilityState.CURRENT_VISIBLE,
                region="center",
                user_label="development laptop",
                stability_score=0.98,
            ),
            TrackedObject(
                track_id="track_003",
                class_id=73,
                class_name="book",
                confidence=0.89,
                raw_bbox=BoundingBox(ymin=0.60, xmin=0.05, ymax=0.95, xmax=0.35),
                smoothed_bbox=BoundingBox(ymin=0.60, xmin=0.05, ymax=0.95, xmax=0.35),
                center_x=0.20,
                center_y=0.775,
                width=0.30,
                height=0.35,
                first_seen_timestamp=1727650000.0,
                last_seen_timestamp=1727650030.0,
                frames_seen=45,
                visibility_state=VisibilityState.CURRENT_VISIBLE,
                region="bottom_left",
                user_label="project notebook",
                ocr_associations=["Embedded System Firmware Notes"],
                ocr_association_conf=0.91,
                stability_score=0.92,
            ),
        ]

    @classmethod
    def get_demo_relations(cls) -> list[SpatialRelation]:
        return [
            SpatialRelation(
                source_track_id="track_001",
                relation_type="right_of",
                target_track_id="track_002",
                source_label="water bottle",
                target_label="laptop",
                description="water bottle is right of laptop",
                confidence=0.95,
            ),
            SpatialRelation(
                source_track_id="track_001",
                relation_type="near",
                target_track_id="track_002",
                source_label="water bottle",
                target_label="laptop",
                description="water bottle is near laptop",
                confidence=0.88,
            ),
            SpatialRelation(
                source_track_id="track_003",
                relation_type="left_of",
                target_track_id="track_002",
                source_label="project notebook",
                target_label="laptop",
                description="project notebook is left of laptop",
                confidence=0.92,
            ),
        ]

    @classmethod
    def get_demo_observations(cls) -> list[WorkspaceObservation]:
        tracks = cls.get_demo_workspace_tracks()
        relations = cls.get_demo_relations()
        obs = []
        for t in tracks:
            rel_strs = [r.description for r in relations if r.source_track_id == t.track_id or r.target_track_id == t.track_id]
            obs.append(
                WorkspaceObservation(
                    track_id=t.track_id,
                    object_label=t.class_name,
                    user_label=t.user_label,
                    aliases=[t.user_label] if t.user_label else [],
                    confidence=t.confidence,
                    last_seen_timestamp=t.last_seen_timestamp,
                    last_seen_bbox=t.smoothed_bbox,
                    normalized_position={"x": t.center_x, "y": t.center_y},
                    region=t.region,
                    visibility_state=t.visibility_state.value if hasattr(t.visibility_state, "value") else str(t.visibility_state),
                    source="DEMO / SIMULATION",
                    ocr_associations=t.ocr_associations,
                    relations=rel_strs,
                )
            )
        return obs

    @classmethod
    def get_demo_memories(cls) -> list[dict[str, Any]]:
        return [
            {
                "id": 901,
                "title": "Electronics Project Notebook",
                "content": "Notes for the Snapdragon IoT development board with temperature sensor and Hexagon NPU acceleration.",
                "category": "Projects",
                "project_id": 1,
                "score": 0.88,
            },
            {
                "id": 902,
                "title": "Desk Hardware Setup",
                "content": "Water bottle kept on the right side of the primary workstation laptop to avoid spills.",
                "category": "Objects",
                "project_id": None,
                "score": 0.85,
            },
        ]

    @classmethod
    def get_demo_documents(cls) -> list[dict[str, Any]]:
        return [
            {
                "document_id": "demo-doc-microcontroller",
                "title": "microcontroller_hardware_manual.pdf",
                "page": 4,
                "chunk_index": 0,
                "content": "Section 4.2: Hardware Timers & PWM Configuration. The onboard timer registers must be initialized at 16 MHz with prescaler 64.",
                "score": 0.91,
            }
        ]

    @classmethod
    def get_demo_evidence(cls) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []
        # Visual objects
        for t in cls.get_demo_workspace_tracks():
            evidence.append(
                EvidenceItem(
                    category=EvidenceCategory.OBSERVED,
                    source_type="VISION",
                    source_id=t.track_id,
                    title=f"Visible: {t.user_label or t.class_name}",
                    snippet=f"Detected {t.class_name} in region '{t.region}' (conf: {t.confidence:.2f})",
                    score=t.confidence,
                    metadata={"bbox": t.smoothed_bbox.model_dump(), "zone": t.region, "mode": cls.DEMO_TAG},
                )
            )
            for text in t.ocr_associations:
                evidence.append(
                    EvidenceItem(
                        category=EvidenceCategory.OBSERVED,
                        source_type="OCR",
                        source_id=f"ocr_{t.track_id}",
                        title=f"OCR on {t.class_name}",
                        snippet=f'Recognized text: "{text}"',
                        score=t.ocr_association_conf,
                        metadata={"track_id": t.track_id, "mode": cls.DEMO_TAG},
                    )
                )

        # Spatial relations
        for r in cls.get_demo_relations():
            evidence.append(
                EvidenceItem(
                    category=EvidenceCategory.INFERRED,
                    source_type="WORKSPACE_TRACK",
                    source_id=f"rel_{r.source_track_id}_{r.target_track_id}",
                    title=f"Spatial: {r.relation_type}",
                    snippet=r.description,
                    score=r.confidence,
                    metadata={"mode": cls.DEMO_TAG},
                )
            )

        # Memories
        for m in cls.get_demo_memories():
            evidence.append(
                EvidenceItem(
                    category=EvidenceCategory.RETRIEVED,
                    source_type="MEMORY",
                    source_id=m["id"],
                    title=m["title"],
                    snippet=m["content"],
                    score=m["score"],
                    metadata={"category": m["category"], "mode": cls.DEMO_TAG},
                )
            )

        # Documents
        for d in cls.get_demo_documents():
            evidence.append(
                EvidenceItem(
                    category=EvidenceCategory.RETRIEVED,
                    source_type="DOCUMENT",
                    source_id=d["document_id"],
                    title=d["title"],
                    snippet=d["content"],
                    page=d["page"],
                    score=d["score"],
                    metadata={"mode": cls.DEMO_TAG},
                )
            )

        return evidence


demo_fixture_service = DemoFixtureService()
