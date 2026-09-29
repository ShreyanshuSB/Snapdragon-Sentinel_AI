from __future__ import annotations

import logging
import time
from typing import Any

from app.ai.reasoning.adapter import (
    GenerationResult,
    LocalCPUReasoningAdapter,
    Qwen3VLModelAdapter,
    ReasoningModelAdapter,
)
from app.ai.reasoning.context_builder import BuiltContext
from app.ai.reasoning.response_validator import ResponseValidator, ValidatedResponse
from app.schemas.chat import TimingMetrics

logger = logging.getLogger(__name__)


class DiagnosticContextRepresentation:
    """Developer-only diagnostic view that strips private text to protect user privacy (Section 40)."""

    def __init__(
        self,
        question_length: int,
        source_count: int,
        source_ids: list[str],
        source_types: list[str],
        estimated_tokens: int,
        dropped_source_ids: list[str],
    ) -> None:
        self.question_length = question_length
        self.source_count = source_count
        self.source_ids = source_ids
        self.source_types = source_types
        self.estimated_tokens = estimated_tokens
        self.dropped_source_ids = dropped_source_ids

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_char_count": self.question_length,
            "source_count": self.source_count,
            "source_ids": self.source_ids,
            "source_types": self.source_types,
            "estimated_tokens": self.estimated_tokens,
            "dropped_source_ids": self.dropped_source_ids,
        }


class ReasoningEngine:
    """
    Core Multimodal Reasoning Engine orchestrating model execution,
    lifecycle management, latency benchmarking, and output validation.
    """

    _instance: ReasoningEngine | None = None

    def __init__(self, adapter: ReasoningModelAdapter | None = None) -> None:
        self.adapter: ReasoningModelAdapter = adapter or Qwen3VLModelAdapter()
        self._state: str = "AVAILABLE"  # AVAILABLE, LOADING, READY, RUNNING, ERROR
        self._last_diagnostics: DiagnosticContextRepresentation | None = None
        self._total_inferences: int = 0
        self._last_generation_ms: float = 0.0

    @classmethod
    def get_instance(cls) -> ReasoningEngine:
        if cls._instance is None:
            cls._instance = ReasoningEngine()
        return cls._instance

    @property
    def state(self) -> str:
        return self._state

    def set_adapter(self, adapter: ReasoningModelAdapter) -> None:
        """Switch or inject a model adapter (e.g. for testing)."""
        self.adapter = adapter
        self._state = "AVAILABLE"

    def load_model(self) -> bool:
        """Load model weights (singleton reuse per Section 30)."""
        if self.adapter.is_loaded():
            self._state = "READY"
            return True

        self._state = "LOADING"
        success = self.adapter.load()
        if success:
            self._state = "READY"
        else:
            self._state = "AVAILABLE"  # Ready to fallback or initialize on request
        return success

    def run_reasoning(
        self,
        built_context: BuiltContext,
        images: list[Any] | None = None,
        retrieval_ms: float = 0.0,
        context_build_ms: float = 0.0,
        image_prepare_ms: float = 0.0,
    ) -> ValidatedResponse:
        t0 = time.perf_counter()

        # Build Section 40 Privacy-Safe Diagnostics
        self._last_diagnostics = DiagnosticContextRepresentation(
            question_length=len(built_context.user_prompt),
            source_count=len(built_context.sources),
            source_ids=[s.id for s in built_context.sources],
            source_types=[s.type for s in built_context.sources],
            estimated_tokens=built_context.estimated_tokens,
            dropped_source_ids=built_context.dropped_sources,
        )

        self._state = "RUNNING"
        try:
            # Ensure model is ready
            if not self.adapter.is_loaded():
                self.load_model()

            gen_result = self.adapter.generate(
                prompt=built_context.user_prompt,
                images=images,
                system_prompt=built_context.system_prompt,
                max_tokens=512,
            )

            gen_ms = gen_result.generation_ms
            self._last_generation_ms = gen_ms
            self._total_inferences += 1
            self._state = "READY"

            total_ms = (time.perf_counter() - t0) * 1000 + retrieval_ms + context_build_ms + image_prepare_ms
            timing = TimingMetrics(
                retrieval_ms=round(retrieval_ms, 2),
                context_build_ms=round(context_build_ms, 2),
                image_prepare_ms=round(image_prepare_ms, 2),
                generation_ms=round(gen_ms, 2),
                total_ms=round(total_ms, 2),
            )

            # Validate and check citations
            validated = ResponseValidator.validate_and_sanitize(
                raw_text=gen_result.text,
                available_sources=built_context.sources,
                model_name=gen_result.model_name,
                runtime_name=gen_result.runtime_name,
                provider_name=gen_result.provider_name,
                device_name=gen_result.device_name,
                npu_verified=gen_result.npu_verified,
                timing=timing,
                raw_status=gen_result.status,
            )
            return validated

        except Exception as e:
            logger.exception("Error during multimodal reasoning execution: %s", e)
            self._state = "ERROR"
            total_ms = (time.perf_counter() - t0) * 1000 + retrieval_ms + context_build_ms + image_prepare_ms
            timing = TimingMetrics(
                retrieval_ms=round(retrieval_ms, 2),
                context_build_ms=round(context_build_ms, 2),
                image_prepare_ms=round(image_prepare_ms, 2),
                generation_ms=0.0,
                total_ms=round(total_ms, 2),
            )
            return ValidatedResponse(
                answer="I encountered an internal error while processing your request.",
                sources=[],
                model_name=self.adapter.model_name,
                runtime_name=self.adapter.runtime.get_name(),
                provider_name=self.adapter.runtime.get_provider_name(),
                device_name=self.adapter.runtime.get_device_name(),
                npu_verified=False,
                timing=timing,
                status="ERROR",
                validation_errors=[str(e)],
            )

    def get_status(self) -> dict[str, Any]:
        meta = self.adapter.get_metadata()
        return {
            "state": self._state,
            "model_name": meta["name"],
            "model_version": meta["version"],
            "runtime": meta["runtime"],
            "execution_provider": meta["execution_provider"],
            "device": meta["device"],
            "npu_verified": meta["npu_verified"],
            "context_length": meta["context_length"],
            "parameter_count": meta["parameter_count"],
            "license": meta["license"],
            "is_loaded": meta["is_loaded"],
            "total_inferences": self._total_inferences,
            "last_generation_ms": round(self._last_generation_ms, 2),
            "diagnostics": self._last_diagnostics.to_dict() if self._last_diagnostics else None,
        }
