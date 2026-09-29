from __future__ import annotations

import re
from typing import Any

from app.schemas.chat import SourceAttribution, TimingMetrics, VerificationInfo


class ValidatedResponse:
    """Encapsulates the thoroughly checked response ready for delivery to user."""

    def __init__(
        self,
        answer: str,
        sources: list[SourceAttribution],
        model_name: str,
        runtime_name: str,
        provider_name: str,
        device_name: str,
        npu_verified: bool,
        timing: TimingMetrics,
        status: str,
        validation_errors: list[str],
        observed_facts: list[str] | None = None,
        retrieved_facts: list[str] | None = None,
        inferred_facts: list[str] | None = None,
        uncertainties: list[str] | None = None,
    ) -> None:
        self.answer = answer
        self.sources = sources
        self.model_name = model_name
        self.runtime_name = runtime_name
        self.provider_name = provider_name
        self.device_name = device_name
        self.npu_verified = npu_verified
        self.timing = timing
        self.status = status
        self.validation_errors = validation_errors
        self.observed_facts = observed_facts or []
        self.retrieved_facts = retrieved_facts or []
        self.inferred_facts = inferred_facts or []
        self.uncertainties = uncertainties or []


class ResponseValidator:
    """
    Validates model output to ensure:
    1. Truthful source citations (rejecting non-existent tags)
    2. Grounded visual observations (rejecting claims of seeing objects without vision input)
    3. Spatial consistency (rejecting hallucinated object locations)
    4. Honest hardware reporting (rejecting false Snapdragon claims on host)
    5. Safe fallbacks for empty or corrupted outputs
    """

    OBSERVATION_PATTERNS = [
        re.compile(r"\b(i see|i can see|is visible|currently visible|on your desk)\b", re.IGNORECASE),
        re.compile(r"\b(looking at|in the camera|in this image)\b", re.IGNORECASE),
    ]

    ZONE_NAMES = [
        "top_left", "top_center", "top_right",
        "center_left", "center", "center_right",
        "bottom_left", "bottom_center", "bottom_right",
        "left", "right", "middle"
    ]

    @classmethod
    def validate_and_sanitize(
        cls,
        raw_text: str | None,
        available_sources: list[SourceAttribution],
        model_name: str,
        runtime_name: str,
        provider_name: str,
        device_name: str,
        npu_verified: bool,
        timing: TimingMetrics,
        raw_status: str = "READY",
    ) -> ValidatedResponse:
        errors: list[str] = []

        # 1. Answer text validation
        if not raw_text or not raw_text.strip():
            answer = "I don't have enough information to determine that."
            errors.append("Model produced empty text; substituted safe fallback.")
            status = "FALLBACK_EMPTY"
        else:
            answer = raw_text.strip()
            status = raw_status

        # 2. Source citation verification: only keep citations that exist in available_sources
        # Match tags like [MEMORY:M1], [DOCUMENT:D2:PAGE:1], [VISION:CURRENT_FRAME], [OCR:CURRENT_FRAME]
        cited_tags = set(re.findall(r"\[(MEMORY:[^\]]+|DOCUMENT:[^\]]+|VISION:[^\]]+|OCR:[^\]]+)\]", answer))

        valid_sources: list[SourceAttribution] = []
        available_ids = {str(s.id): s for s in available_sources}

        if cited_tags:
            for tag in cited_tags:
                if tag in available_ids:
                    valid_sources.append(available_ids[tag])
                else:
                    errors.append(f"Model cited non-existent source tag: {tag}")
                    # Remove the invalid bracket tag from user-facing text to prevent confusion
                    answer = answer.replace(f"[{tag}]", "")
            # Clean up potential double spaces from tag stripping
            answer = re.sub(r" +", " ", answer).strip()

        # If no explicit tags were found, retain available sources in the context
        if not valid_sources:
            valid_sources = available_sources

        # 3. Direct visual observation validation:
        # If model claims to visually see something, verify that visual sources exist
        has_vision_source = any(s.type in ("VISION", "OCR") for s in available_sources)
        claims_observation = any(p.search(answer) for p in cls.OBSERVATION_PATTERNS)

        if claims_observation and not has_vision_source:
            errors.append("Model claimed direct visual observation without active vision or camera evidence.")
            # Downgrade claim
            answer = f"Note: No active camera feed or image is attached. {answer}"
            status = "DOWNGRADED_NO_VISION"

        # 4. Location hallucination check:
        # If model asserts an object is in a specific zone, cross-check against available vision sources
        vision_sources = [s for s in available_sources if s.type in ("VISION", "OCR")]
        if claims_observation and vision_sources:
            # Check if mentioned zone exists in any vision source snippet
            for zone in cls.ZONE_NAMES:
                if re.search(rf"\b{zone}\b", answer, re.IGNORECASE):
                    zone_grounded = any(zone.replace("_", " ") in (s.snippet or "").lower() or zone in (s.snippet or "").lower() for s in vision_sources)
                    if not zone_grounded:
                        errors.append(f"Model claimed object is in '{zone}', which is not confirmed by vision evidence.")

        # 5. Hardware metadata validation: enforce truthful NPU verification
        if "Intel" in device_name and npu_verified:
            npu_verified = False
            errors.append("Invalid state: Host Intel CPU cannot claim verified Snapdragon NPU.")

        # 6. Categorize statements into epistemic tiers
        observed_facts: list[str] = []
        retrieved_facts: list[str] = []
        inferred_facts: list[str] = []
        uncertainties: list[str] = []

        for line in answer.split("."):
            line_s = line.strip()
            if not line_s:
                continue
            lower_line = line_s.lower()
            if any(w in lower_line for w in ["cannot determine", "don't have enough", "not found", "unknown", "uncertain", "missing"]):
                uncertainties.append(line_s)
            elif any(w in lower_line for w in ["i see", "detected", "visible", "looking at", "ocr text"]):
                observed_facts.append(line_s)
            elif any(w in lower_line for w in ["you saved", "saved in", "notes state", "document says", "according to your memory", "previously saved"]):
                retrieved_facts.append(line_s)
            elif any(w in lower_line for w in ["appears to be", "next to", "near", "likely", "suggests", "seems"]):
                inferred_facts.append(line_s)

        return ValidatedResponse(
            answer=answer,
            sources=valid_sources,
            model_name=model_name or "Unknown-Model",
            runtime_name=runtime_name or "CPUExecutionProvider",
            provider_name=provider_name or "CPUExecutionProvider",
            device_name=device_name or "Host CPU (Intel)",
            npu_verified=npu_verified,
            timing=timing,
            status=status,
            validation_errors=errors,
            observed_facts=observed_facts,
            retrieved_facts=retrieved_facts,
            inferred_facts=inferred_facts,
            uncertainties=uncertainties,
        )
