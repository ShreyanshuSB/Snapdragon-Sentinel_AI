from __future__ import annotations

import re
import time
from typing import Sequence
from app.ai.vision.tracking.models import (
    FindItCandidate,
    FindItResponse,
    VisibilityState,
    WorkspaceObservation,
)
from app.ai.vision.tracking.workspace_state import OBJECT_ALIASES, workspace_state


class FindItService:
    """
    Resolves natural language queries ('Where is my water bottle?', 'Find the laptop',
    'What is next to my keyboard?') against current and recent workspace observations.
    Enforces absolute truthfulness and uncertainty states without fabricating locations.
    """

    def __init__(self, state=None) -> None:
        self.state = state or workspace_state

    def query(
        self,
        query_text: str | Any,
        project_id: str | None = None,
        target_label: str | None = None,
        current_time: float | None = None,
    ) -> FindItResponse:
        if hasattr(query_text, "query"):
            target_label = getattr(query_text, "target_label", None)
            project_id = getattr(query_text, "project_id", None)
            query_text = str(query_text.query)

        now = current_time if current_time is not None else time.time()
        observations = self.state.get_recent_observations(current_time=now)

        # 1. Project filtering: if project_id is specified, filter observations
        if project_id:
            observations = [obs for obs in observations if obs.project_id is None or obs.project_id == project_id]

        if not observations:
            return FindItResponse(
                found=False,
                match_type="NOT_FOUND",
                object=target_label or query_text.strip(),
                message="I can't find a matching object in the current workspace observations.",
                candidates=[],
                relations=[],
            )

        # 2. Extract query tokens and intent
        clean_query = query_text.lower().strip()
        clean_target = (target_label.lower().strip() if target_label else None)

        # Check for relational query: "what is next to my keyboard?", "what is near the laptop?"
        relational_target = self._extract_relational_target(clean_query)
        if relational_target:
            return self._resolve_relational_query(relational_target, observations, now)

        # 3. Match candidate objects using hierarchical resolution
        candidates = self._score_candidates(clean_query, clean_target, observations, now)

        if not candidates:
            return FindItResponse(
                found=False,
                match_type="NOT_FOUND",
                object=clean_target or clean_query,
                message=f"I can't currently see '{clean_target or clean_query}' on the desk.",
                candidates=[],
                relations=[],
            )

        # 4. Check for ambiguity
        # If multiple candidates have very similar high scores (> 0.7) and same object label
        if len(candidates) > 1 and abs(candidates[0]["score"] - candidates[1]["score"]) < 0.15:
            cand_models = [self._to_candidate_model(c, now) for c in candidates[:4]]
            obj_name = candidates[0]["obs"].object_label
            return FindItResponse(
                found=True,
                match_type="AMBIGUOUS",
                object=obj_name,
                message=f"I can see {len(candidates)} {obj_name}s on the desk. Which one do you mean?",
                candidates=cand_models,
                relations=candidates[0]["obs"].relations,
                grounding_box=candidates[0]["obs"].last_seen_bbox,
            )

        # 5. Best match selected
        best = candidates[0]
        best_obs: WorkspaceObservation = best["obs"]
        age_seconds = round(now - best_obs.last_seen_timestamp, 1)

        display_name = best_obs.user_label or best_obs.object_label

        # Map visibility state
        if best_obs.visibility_state == VisibilityState.CURRENT_VISIBLE.value and age_seconds <= 3.0:
            match_type = "CURRENT_VISIBLE"
            msg = f"Your {display_name} is located in the {best_obs.region} area of the desk."
        elif best_obs.visibility_state == VisibilityState.RECENTLY_SEEN.value or age_seconds <= 15.0:
            match_type = "RECENTLY_SEEN"
            msg = f"The {display_name} was last seen {age_seconds} seconds ago near the {best_obs.region}."
        else:
            match_type = "STALE"
            msg = f"The {display_name} was visible {age_seconds} seconds ago, but is no longer in view."

        return FindItResponse(
            found=True,
            match_type=match_type,
            object=display_name,
            track_id=best_obs.track_id,
            confidence=round(best_obs.confidence, 2),
            region=best_obs.region,
            normalized_position=best_obs.normalized_position,
            last_seen=f"{age_seconds}s ago" if age_seconds >= 1.0 else "just now",
            age_seconds=age_seconds,
            relations=best_obs.relations,
            candidates=[self._to_candidate_model(best, now)],
            message=msg,
            grounding_box=best_obs.last_seen_bbox,
        )

    def _score_candidates(
        self,
        query: str,
        target_label: str | None,
        observations: Sequence[WorkspaceObservation],
        now: float,
    ) -> list[dict]:
        """Score each observation against query terms."""
        scored: list[dict] = []

        query_tokens = set(re.findall(r"\b[a-z0-9]+\b", query))

        for obs in observations:
            score = 0.0
            obj_lower = obs.object_label.lower()
            user_lbl = (obs.user_label.lower() if obs.user_label else "")

            # 1. Exact user label match (Highest priority)
            if user_lbl and (user_lbl in query or query in user_lbl):
                score = max(score, 1.0)
            elif user_lbl:
                user_tokens = set(re.findall(r"\b[a-z0-9]+\b", user_lbl))
                if user_tokens & query_tokens:
                    score = max(score, 0.90)

            # 2. Target label match if explicitly provided
            if target_label:
                if target_label in obj_lower or obj_lower in target_label:
                    score = max(score, 0.95)

            # 3. Exact object class match
            if obj_lower in query:
                score = max(score, 0.85)

            # 4. Synonym / alias match
            for alias in obs.aliases:
                if alias in query:
                    score = max(score, 0.80)
                    break

            # 5. Global alias lookup match
            class_aliases = OBJECT_ALIASES.get(obj_lower, [])
            for alias in class_aliases:
                if alias in query:
                    score = max(score, 0.80)
                    break

            # 6. OCR associated text match
            for ocr_text in obs.ocr_associations:
                ocr_clean = ocr_text.lower()
                if ocr_clean in query or query in ocr_clean:
                    score = max(score, 0.85)
                    break
                ocr_tokens = set(re.findall(r"\b[a-z0-9]+\b", ocr_clean))
                if ocr_tokens & query_tokens:
                    score = max(score, 0.75)
                    break

            # Deduct score slightly for older / stale observations
            age = now - obs.last_seen_timestamp
            recency_penalty = min(0.30, age * 0.01)
            final_score = round(max(0.0, score - recency_penalty), 3)

            if final_score >= 0.50:
                scored.append({"obs": obs, "score": final_score})

        # Sort by score descending
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def _extract_relational_target(self, query: str) -> str | None:
        """Extract anchor entity for queries like 'what is next to my keyboard?'"""
        patterns = [
            r"(?:what is|what's|find what is)\s+(?:next to|near|beside|by|around)\s+(?:my\s+|the\s+)?([a-z0-9_ ]+)",
            r"(?:what is|what's)\s+(?:left of|right of|above|below)\s+(?:my\s+|the\s+)?([a-z0-9_ ]+)",
        ]
        for pat in patterns:
            m = re.search(pat, query)
            if m:
                target = m.group(1).strip()
                # Clean punctuation
                target = re.sub(r"[?!.]", "", target).strip()
                return target
        return None

    def _resolve_relational_query(
        self,
        relational_target: str,
        observations: Sequence[WorkspaceObservation],
        now: float,
    ) -> FindItResponse:
        """Find an anchor object and return what is near / next to it."""
        # Find anchor
        anchor_candidates = self._score_candidates(relational_target, None, observations, now)
        if not anchor_candidates:
            return FindItResponse(
                found=False,
                match_type="NOT_FOUND",
                object=relational_target,
                message=f"I can't locate '{relational_target}' on the desk to see what is next to it.",
                candidates=[],
                relations=[],
            )

        anchor = anchor_candidates[0]["obs"]
        anchor_label = anchor.user_label or anchor.object_label

        # Look for neighboring objects
        neighbors: list[WorkspaceObservation] = []
        for obs in observations:
            if obs.track_id == anchor.track_id:
                continue
            # Check relations
            for rel in obs.relations:
                if anchor_label in rel:
                    neighbors.append(obs)
                    break

        if not neighbors:
            return FindItResponse(
                found=True,
                match_type="CURRENT_VISIBLE" if anchor.visibility_state == VisibilityState.CURRENT_VISIBLE.value else "RECENTLY_SEEN",
                object=anchor_label,
                track_id=anchor.track_id,
                region=anchor.region,
                normalized_position=anchor.normalized_position,
                message=f"Found {anchor_label} in the {anchor.region} area, but there are no other detected objects next to it.",
                relations=anchor.relations,
                grounding_box=anchor.last_seen_bbox,
            )

        best_neighbor = neighbors[0]
        neigh_label = best_neighbor.user_label or best_neighbor.object_label

        # Find matching relation description
        matched_rel = ""
        for r in best_neighbor.relations:
            if anchor_label in r:
                matched_rel = r
                break

        msg = f"The {neigh_label} is next to {anchor_label} ({matched_rel or best_neighbor.region})."
        return FindItResponse(
            found=True,
            match_type="CURRENT_VISIBLE" if best_neighbor.visibility_state == VisibilityState.CURRENT_VISIBLE.value else "RECENTLY_SEEN",
            object=neigh_label,
            track_id=best_neighbor.track_id,
            region=best_neighbor.region,
            normalized_position=best_neighbor.normalized_position,
            message=msg,
            relations=best_neighbor.relations,
            candidates=[self._to_candidate_model({"obs": best_neighbor, "score": 1.0}, now)],
            grounding_box=best_neighbor.last_seen_bbox,
        )

    def _to_candidate_model(self, item: dict, now: float) -> FindItCandidate:
        obs: WorkspaceObservation = item["obs"]
        age = round(now - obs.last_seen_timestamp, 1)
        return FindItCandidate(
            track_id=obs.track_id,
            object=obs.object_label,
            user_label=obs.user_label,
            confidence=round(obs.confidence, 2),
            region=obs.region,
            normalized_position=obs.normalized_position,
            last_seen=f"{age}s ago" if age >= 1.0 else "just now",
            age_seconds=age,
            relations=obs.relations,
            bbox=obs.last_seen_bbox,
        )


find_it_service = FindItService()
