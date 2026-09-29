from __future__ import annotations

import logging
import re
from typing import Any

from app.schemas.speech import VoiceActionResult, VoiceIntentType
from app.ai.vision.tracking.find_it import find_it_service
from app.ai.vision.tracking.models import FindItRequest, MatchType
from app.ai.vision.tracking.workspace_state import workspace_state
from app.services.memory_service import memory_service
from app.services.document_service import document_service

logger = logging.getLogger(__name__)


class VoiceActionRouter:
    """
    Deterministic intent classifier and action dispatcher for spoken transcripts.
    Directs spoken queries into Find It, Workspace Memory, Document Retrieval,
    or Ask SENTINEL multimodal reasoning.
    """

    FIND_IT_PATTERNS = [
        re.compile(r"^(?:where\s+is|where\'s|wheres)\s+(?:the\s+|my\s+|that\s+)?(.+?)[\?\.]*$", re.IGNORECASE),
        re.compile(r"^find\s+(?:the\s+|my\s+|that\s+)?(.+?)[\?\.]*$", re.IGNORECASE),
        re.compile(r"^is\s+(?:the\s+|my\s+|that\s+)?(.+?)\s+on\s+the\s+desk[\?\.]*$", re.IGNORECASE),
        re.compile(r"^locate\s+(?:the\s+|my\s+|that\s+)?(.+?)[\?\.]*$", re.IGNORECASE),
        re.compile(r"^where\s+was\s+(?:the\s+|my\s+|that\s+)?(.+?)\s+last\s+seen[\?\.]*$", re.IGNORECASE),
        re.compile(r"^show\s+me\s+(?:the\s+|my\s+|that\s+)?(.+?)[\?\.]*$", re.IGNORECASE),
    ]

    REMEMBER_PATTERNS = [
        re.compile(r"^remember\s+this\s+(?:object\s+)?as\s+(.+)[\?\.]*$", re.IGNORECASE),
        re.compile(r"^remember\s+this\s+is\s+(.+)[\?\.]*$", re.IGNORECASE),
        re.compile(r"^call\s+this\s+(?:object\s+)?(.+)[\?\.]*$", re.IGNORECASE),
        re.compile(r"^save\s+this\s+(?:object\s+)?as\s+(.+)[\?\.]*$", re.IGNORECASE),
        re.compile(r"^remember\s+(?:that\s+)?(.+?)\s+as\s+(.+)[\?\.]*$", re.IGNORECASE),
    ]

    SEARCH_MEMORY_PATTERNS = [
        re.compile(r"^what\s+did\s+i\s+(?:save|write|note|remember)\s+(?:about|on|for)\s+(.+)[\?\.]*$", re.IGNORECASE),
        re.compile(r"^search\s+memory\s+for\s+(.+)[\?\.]*$", re.IGNORECASE),
        re.compile(r"^recall\s+(?:my\s+)?(.+)[\?\.]*$", re.IGNORECASE),
        re.compile(r"^what\s+do\s+i\s+remember\s+about\s+(.+)[\?\.]*$", re.IGNORECASE),
    ]

    SEARCH_DOCS_PATTERNS = [
        re.compile(r"^(?:find|search)\s+(?:the\s+)?document(?:s)?\s+(?:about|for)?\s*(.+)[\?\.]*$", re.IGNORECASE),
        re.compile(r"^what\s+does\s+the\s+document\s+say\s+about\s+(.+)[\?\.]*$", re.IGNORECASE),
        re.compile(r"^search\s+docs\s+for\s+(.+)[\?\.]*$", re.IGNORECASE),
    ]

    ASK_WORKSPACE_PATTERNS = [
        re.compile(r"^what\s+am\s+i\s+looking\s+at[\?\.]*$", re.IGNORECASE),
        re.compile(r"^what(?:\'s|\s+is)\s+on\s+(?:my\s+|the\s+)?desk[\?\.]*$", re.IGNORECASE),
        re.compile(r"^describe\s+(?:the\s+|my\s+)?workspace[\?\.]*$", re.IGNORECASE),
        re.compile(r"^what\s+objects\s+do\s+you\s+see[\?\.]*$", re.IGNORECASE),
    ]

    def route(
        self,
        transcript: str,
        project_id: str = "default",
        db: Any = None,
    ) -> VoiceActionResult:
        cleaned = transcript.strip()
        if not cleaned:
            return VoiceActionResult(
                intent=VoiceIntentType.UNKNOWN,
                summary="No speech detected in audio.",
                raw_query="",
            )

        # 1. Check REMEMBER_OBJECT
        for pat in self.REMEMBER_PATTERNS:
            m = pat.match(cleaned)
            if m:
                if len(m.groups()) == 2:
                    alias = m.group(2).strip()
                else:
                    alias = m.group(1).strip()
                return self._handle_remember_object(alias, project_id, db=db)

        # 2. Check SEARCH_DOCS (must precede generic "find ...")
        for pat in self.SEARCH_DOCS_PATTERNS:
            m = pat.match(cleaned)
            if m:
                query = m.group(1).strip()
                return self._handle_search_documents(query, project_id, db=db)

        # 3. Check SEARCH_MEMORY
        for pat in self.SEARCH_MEMORY_PATTERNS:
            m = pat.match(cleaned)
            if m:
                query = m.group(1).strip()
                return self._handle_search_memory(query, project_id, db=db)

        # 4. Check ASK_WORKSPACE / ASK_SENTINEL
        for pat in self.ASK_WORKSPACE_PATTERNS:
            m = pat.match(cleaned)
            if m:
                return self._handle_ask_workspace(cleaned, project_id)

        # 5. Check FIND_IT
        for pat in self.FIND_IT_PATTERNS:
            m = pat.match(cleaned)
            if m:
                target_query = m.group(1).strip()
                return self._handle_find_it(target_query, project_id)

        # 6. Fallback to GENERAL_QUERY (Natural language question)
        return VoiceActionResult(
            intent=VoiceIntentType.GENERAL_QUERY,
            summary=f"Processed query: '{cleaned}'",
            raw_query=cleaned,
            action_data={"query": cleaned, "project_id": project_id},
        )

    def _handle_find_it(self, target_query: str, project_id: str) -> VoiceActionResult:
        res = find_it_service.query(query_text=target_query, project_id=project_id)

        relations_str = ", ".join(res.relations) if res.relations else ""

        if res.found and res.match_type == MatchType.CURRENT_VISIBLE:
            conf_str = f"({res.confidence:.0%})" if res.confidence is not None else "(90%)"
            summary = f"Found {res.object or target_query} in the {res.region or 'workspace'} {conf_str}."
            if relations_str:
                summary += f" Nearby: {relations_str}."
            grounding_act = {
                "action": "HIGHLIGHT_OBJECT",
                "target_id": res.track_id,
                "label": res.object,
                "box_2d": res.grounding_box.model_dump() if res.grounding_box else None,
                "zone": res.region,
                "confidence": res.confidence,
                "description": summary,
            }
            return VoiceActionResult(
                intent=VoiceIntentType.FIND_IT,
                summary=summary,
                raw_query=target_query,
                grounded_target_id=res.track_id,
                grounded_target_name=res.object,
                grounded_region=res.region,
                grounded_confidence=res.confidence,
                grounded_relations=res.relations,
                grounding_action=grounding_act,
                action_data=res.model_dump(),
            )

        elif res.found and res.match_type == MatchType.RECENTLY_SEEN:
            age = f"{res.age_seconds:.1f}" if res.age_seconds else "a few"
            summary = (
                f"I can't currently see it. It was last seen in {res.region or 'the workspace'} "
                f"{age} seconds ago."
            )
            return VoiceActionResult(
                intent=VoiceIntentType.FIND_IT,
                summary=summary,
                raw_query=target_query,
                grounded_target_id=res.track_id,
                grounded_target_name=res.object,
                grounded_region=res.region,
                grounded_confidence=res.confidence,
                grounded_relations=res.relations,
                action_data=res.model_dump(),
            )
        elif res.match_type == MatchType.AMBIGUOUS:
            names = [getattr(c, "object_label", None) or getattr(c, "object", "item") for c in res.candidates[:3]]
            summary = f"I see multiple matching candidates ({', '.join(names)}). Which one do you mean?"
            return VoiceActionResult(
                intent=VoiceIntentType.FIND_IT,
                summary=summary,
                raw_query=target_query,
                grounded_target_id=None,
                action_data=res.model_dump(),
            )
        else:
            # NOT_FOUND or STALE - Never fabricate coordinates
            return VoiceActionResult(
                intent=VoiceIntentType.FIND_IT,
                summary=f"I can't find '{target_query}' in current or recent workspace observations.",
                raw_query=target_query,
                grounded_target_id=None,
                action_data=res.model_dump(),
            )

    def _handle_remember_object(self, user_label: str, project_id: str, db: Any = None) -> VoiceActionResult:
        active_tracks = workspace_state.get_active_tracks()

        if active_tracks:
            # Bind user label to the most salient active track
            target_track = active_tracks[0]
            workspace_state.remember_object(
                user_label=user_label,
                track_id=target_track.track_id,
                project_id=project_id,
            )
            summary = f"Remembered active object '{target_track.class_name}' as '{user_label}'."
            return VoiceActionResult(
                intent=VoiceIntentType.REMEMBER_OBJECT,
                summary=summary,
                raw_query=user_label,
                grounded_target_id=target_track.track_id,
                grounded_target_name=user_label,
                grounded_region=str(target_track.region.value if hasattr(target_track.region, "value") else target_track.region) if target_track.region else None,
                grounded_confidence=target_track.confidence,
                action_data={"track_id": target_track.track_id, "user_label": user_label},
            )
        else:
            # No active visual track in view, but store alias for workspace context
            workspace_state.remember_object(
                user_label=user_label,
                track_id=None,
                project_id=project_id,
            )
            summary = f"Stored '{user_label}' as a remembered workspace alias."
            return VoiceActionResult(
                intent=VoiceIntentType.REMEMBER_OBJECT,
                summary=summary,
                raw_query=user_label,
                action_data={"user_label": user_label, "note": "No active track in view"},
            )

    def _handle_search_memory(self, query: str, project_id: str, db: Any = None) -> VoiceActionResult:
        if db is not None:
            results = memory_service.search_memories(
                db=db,
                query=query,
                project_id=project_id,
                limit=3,
            )
            if results:
                best = results[0]
                summary = f"From your memory: \"{best.content[:140]}...\""
                return VoiceActionResult(
                    intent=VoiceIntentType.SEARCH_MEMORY,
                    summary=summary,
                    raw_query=query,
                    action_data={"count": len(results), "top_result": best.content},
                )

        return VoiceActionResult(
            intent=VoiceIntentType.SEARCH_MEMORY,
            summary=f"Searching memory for: '{query}'",
            raw_query=query,
            action_data={"query": query, "project_id": project_id},
        )

    def _handle_search_documents(self, query: str, project_id: str, db: Any = None) -> VoiceActionResult:
        if db is not None:
            results = document_service.search_documents(
                db=db,
                query=query,
                project_id=project_id,
                limit=3,
            )
            if results:
                best = results[0]
                summary = f"Found in document '{best.document_title}': \"{best.text[:120]}...\""
                return VoiceActionResult(
                    intent=VoiceIntentType.SEARCH_DOCUMENTS,
                    summary=summary,
                    raw_query=query,
                    action_data={"count": len(results), "top_match": best.text},
                )

        return VoiceActionResult(
            intent=VoiceIntentType.SEARCH_DOCUMENTS,
            summary=f"Searching documents for: '{query}'",
            raw_query=query,
            action_data={"query": query, "project_id": project_id},
        )

    def _handle_ask_workspace(self, query: str, project_id: str) -> VoiceActionResult:
        active_tracks = workspace_state.get_active_tracks()
        if active_tracks:
            items = [f"{t.user_label or t.class_name} in {t.region.value if hasattr(t.region, 'value') else t.region or 'desk'}" for t in active_tracks]
            summary = f"I see {len(active_tracks)} object(s) on your workspace: {', '.join(items)}."
        else:
            summary = "The workspace camera does not currently detect any objects."

        return VoiceActionResult(
            intent=VoiceIntentType.ASK_SENTINEL,
            summary=summary,
            raw_query=query,
            action_data={"active_objects": len(active_tracks)},
        )


voice_router = VoiceActionRouter()
