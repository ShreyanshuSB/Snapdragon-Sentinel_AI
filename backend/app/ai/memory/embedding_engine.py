from __future__ import annotations

import logging
import threading
import time
from typing import Any

import numpy as np

from app.ai.memory.embedding_adapter import (
    EmbeddingModelAdapter,
    SentenceTransformerEmbeddingAdapter,
)
from app.ai.pipeline import ModelLifecycleState
from app.schemas.memory import EmbeddingModelMetadata, EmbeddingStatusResponse

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """
    Thread-safe lifecycle and vector manager for local text embeddings.
    Validates numeric vectors (dimensions, finiteness, non-null), handles binary BLOB
    serialization/deserialization, computes numerically-safe cosine similarity,
    and performs duplicate detection.
    """

    def __init__(self, adapter: EmbeddingModelAdapter | None = None) -> None:
        self._lock = threading.RLock()
        self._adapter: EmbeddingModelAdapter = adapter or SentenceTransformerEmbeddingAdapter()
        self._state: ModelLifecycleState = (
            ModelLifecycleState.AVAILABLE if self._adapter.is_available() else ModelLifecycleState.UNAVAILABLE
        )
        self._total_inferences: int = 0
        self._last_embed_ms: float | None = None
        self._last_query_embed_ms: float | None = None
        self._last_load_ms: float | None = None

    @property
    def state(self) -> ModelLifecycleState:
        return self._state

    def is_available(self) -> bool:
        return self._adapter.is_available()

    def is_loaded(self) -> bool:
        return self._adapter.is_loaded()

    def get_dimension(self) -> int:
        return self._adapter.get_dimension()

    def set_adapter(self, adapter: EmbeddingModelAdapter) -> None:
        with self._lock:
            if self._adapter.is_loaded():
                self._adapter.unload()
            self._adapter = adapter
            self._state = (
                ModelLifecycleState.AVAILABLE if self._adapter.is_available() else ModelLifecycleState.UNAVAILABLE
            )

    def ensure_loaded(self) -> None:
        with self._lock:
            if not self._adapter.is_loaded():
                self._state = ModelLifecycleState.LOADING
                try:
                    t0 = time.perf_counter()
                    self._adapter.load()
                    self._last_load_ms = (time.perf_counter() - t0) * 1000.0
                    self._state = ModelLifecycleState.READY
                except Exception as e:
                    self._state = ModelLifecycleState.ERROR
                    logger.exception("Failed to load embedding adapter: %s", e)
                    raise

    def unload(self) -> None:
        with self._lock:
            self._adapter.unload()
            self._state = (
                ModelLifecycleState.AVAILABLE if self._adapter.is_available() else ModelLifecycleState.UNAVAILABLE
            )

    def _validate_vector(self, vec: np.ndarray, expected_dim: int) -> np.ndarray:
        """
        Validates that vector is non-null, 1D float32, matches expected dimension,
        and contains exclusively finite values (no NaN, no Inf).
        """
        if vec is None:
            raise ValueError("Vector cannot be None.")
        if not isinstance(vec, np.ndarray):
            vec = np.asarray(vec, dtype=np.float32)
        if vec.ndim != 1 or vec.shape[0] != expected_dim:
            raise ValueError(f"Vector dimension mismatch: expected ({expected_dim},), got {vec.shape}")
        if not np.all(np.isfinite(vec)):
            raise ValueError("Vector contains non-finite values (NaN or Infinity).")
        return vec.astype(np.float32)

    def _validate_batch(self, vecs: np.ndarray, expected_dim: int, expected_count: int) -> np.ndarray:
        """
        Validates 2D batch of vectors.
        """
        if vecs is None:
            raise ValueError("Batch vectors cannot be None.")
        if not isinstance(vecs, np.ndarray):
            vecs = np.asarray(vecs, dtype=np.float32)
        if vecs.ndim != 2 or vecs.shape != (expected_count, expected_dim):
            raise ValueError(f"Batch dimension mismatch: expected ({expected_count}, {expected_dim}), got {vecs.shape}")
        if not np.all(np.isfinite(vecs)):
            raise ValueError("Batch vectors contain non-finite values (NaN or Infinity).")
        return vecs.astype(np.float32)

    def embed_text(self, text: str, is_query: bool = False) -> tuple[np.ndarray, float]:
        """
        Embeds a single string and returns (validated_normalized_vector, latency_ms).
        """
        with self._lock:
            self.ensure_loaded()
            self._state = ModelLifecycleState.RUNNING
            t0 = time.perf_counter()
            try:
                raw_vec = self._adapter.embed_text(text, is_query=is_query)
                latency_ms = (time.perf_counter() - t0) * 1000.0
                vec = self._validate_vector(raw_vec, self._adapter.get_dimension())
                self._total_inferences += 1
                self._last_embed_ms = latency_ms
                if is_query:
                    self._last_query_embed_ms = latency_ms
                self._state = ModelLifecycleState.READY
                return vec, latency_ms
            except Exception:
                self._state = ModelLifecycleState.READY
                raise

    def embed_batch(self, texts: list[str], is_query: bool = False) -> tuple[np.ndarray, float]:
        """
        Embeds a list of strings and returns (validated_normalized_matrix, latency_ms).
        """
        if not texts:
            dim = self._adapter.get_dimension()
            return np.empty((0, dim), dtype=np.float32), 0.0

        with self._lock:
            self.ensure_loaded()
            self._state = ModelLifecycleState.RUNNING
            t0 = time.perf_counter()
            try:
                raw_vecs = self._adapter.embed_batch(texts, is_query=is_query)
                latency_ms = (time.perf_counter() - t0) * 1000.0
                vecs = self._validate_batch(raw_vecs, self._adapter.get_dimension(), len(texts))
                self._total_inferences += len(texts)
                self._last_embed_ms = latency_ms
                self._state = ModelLifecycleState.READY
                return vecs, latency_ms
            except Exception:
                self._state = ModelLifecycleState.READY
                raise

    @staticmethod
    def vector_to_bytes(vec: np.ndarray) -> bytes:
        """Converts numpy float32 array to binary bytes for SQLite BLOB storage."""
        if vec is None:
            raise ValueError("Cannot serialize None vector")
        return vec.astype(np.float32).tobytes()

    @staticmethod
    def bytes_to_vector(b: bytes, expected_dim: int | None = None) -> np.ndarray:
        """
        Restores binary bytes from SQLite BLOB to numpy float32 array.
        Validates expected dimension if specified.
        """
        if not b:
            raise ValueError("Cannot decode empty bytes into vector")
        vec = np.frombuffer(b, dtype=np.float32)
        if expected_dim is not None and vec.shape[0] != expected_dim:
            raise ValueError(f"Corrupt or mismatched vector: expected {expected_dim} floats, got {vec.shape[0]}")
        return vec

    @staticmethod
    def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Computes cosine similarity between two float32 vectors.
        Numerically safe: handles None, dimension mismatch, zero vectors, NaN, and Inf without crashing.
        Clamped to [0.0, 1.0].
        """
        if vec1 is None or vec2 is None:
            return 0.0
        if not isinstance(vec1, np.ndarray) or not isinstance(vec2, np.ndarray):
            return 0.0
        if vec1.shape != vec2.shape or vec1.size == 0:
            return 0.0
        if not np.all(np.isfinite(vec1)) or not np.all(np.isfinite(vec2)):
            return 0.0

        norm1 = float(np.linalg.norm(vec1))
        norm2 = float(np.linalg.norm(vec2))
        if norm1 <= 1e-12 or norm2 <= 1e-12:
            return 0.0

        dot = float(np.dot(vec1, vec2))
        sim = dot / (norm1 * norm2)
        if not np.isfinite(sim):
            return 0.0
        return float(max(0.0, min(1.0, sim)))

    def check_duplicate(
        self,
        candidate_text: str,
        existing_items: list[tuple[int, str, str, bytes]],
        threshold: float = 0.85,
    ) -> tuple[bool, float, int | None, str | None]:
        """
        Checks if candidate text is lexically or semantically duplicate to any existing item.

        Args:
            candidate_text: The new text to test.
            existing_items: List of (id, title, content, embedding_bytes).
            threshold: Similarity threshold (default 0.85).

        Returns:
            (is_duplicate, max_similarity, matched_id, matched_title)
        """
        clean_candidate = candidate_text.strip()
        if not clean_candidate or not existing_items:
            return False, 0.0, None, None

        # 1. Exact normalized text match check
        norm_candidate = " ".join(clean_candidate.lower().split())
        for item_id, title, content, _ in existing_items:
            norm_existing = " ".join(f"{title} {content}".lower().split())
            if norm_candidate == norm_existing or norm_candidate == " ".join(content.lower().split()):
                return True, 1.0, item_id, title

        # 2. Semantic similarity check
        cand_vec, _ = self.embed_text(clean_candidate, is_query=False)
        highest_sim = 0.0
        best_match_id: int | None = None
        best_match_title: str | None = None
        dim = self._adapter.get_dimension()

        for item_id, title, _, emb_bytes in existing_items:
            if not emb_bytes:
                continue
            try:
                item_vec = self.bytes_to_vector(emb_bytes, expected_dim=dim)
                sim = self.cosine_similarity(cand_vec, item_vec)
                if sim > highest_sim:
                    highest_sim = sim
                    best_match_id = item_id
                    best_match_title = title
            except Exception:
                continue

        is_dup = highest_sim >= threshold
        return is_dup, round(highest_sim, 4), best_match_id, best_match_title

    def get_metadata(self) -> EmbeddingModelMetadata:
        return self._adapter.get_metadata()

    def get_status(
        self,
        ready_count: int = 0,
        stale_count: int = 0,
        failed_count: int = 0,
        reindex_required: bool = False,
    ) -> EmbeddingStatusResponse:
        meta = self.get_metadata()
        runtime_adapter = self._adapter.get_runtime_adapter()

        return EmbeddingStatusResponse(
            state=self._state.value,
            is_available=self.is_available(),
            is_loaded=self.is_loaded(),
            model=meta,
            ready_memories_count=ready_count,
            stale_memories_count=stale_count,
            failed_memories_count=failed_count,
            reindex_required=reindex_required,
            device_label=runtime_adapter.get_device_label(),
            last_query_embed_ms=round(self._last_query_embed_ms, 2) if self._last_query_embed_ms else None,
            target_model_name="nomic-embed-text-v1.5",
            target_device="Snapdragon X Elite NPU (Hexagon)",
            npu_status="NOT VERIFIED",
        )


# Global thread-safe singleton
embedding_engine = EmbeddingEngine()
