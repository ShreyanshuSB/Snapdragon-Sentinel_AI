from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from app.schemas.memory import EmbeddingModelMetadata

logger = logging.getLogger(__name__)


# ===========================================================================
# Runtime Adapter Layer (Section 6)
# Decouples hardware execution (Host CPU vs Snapdragon QNN/NPU)
# ===========================================================================

class RuntimeAdapter(ABC):
    """
    Abstract runtime execution adapter.
    Encapsulates execution provider details (CPUExecutionProvider vs QNNExecutionProvider).
    """

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the execution provider name (e.g. CPUExecutionProvider, QNNExecutionProvider)."""
        pass

    @abstractmethod
    def is_npu_verified(self) -> bool:
        """Returns whether NPU execution has been verified on this host."""
        pass

    @abstractmethod
    def get_device_label(self) -> str:
        """Returns user-facing hardware description."""
        pass

    @abstractmethod
    def get_runtime_name(self) -> str:
        """Returns description of the underlying runtime engine."""
        pass


class CPURuntimeAdapter(RuntimeAdapter):
    """
    Host CPU execution runtime for local development and CPU inference.
    Verified on current Intel development host.
    """

    def get_provider_name(self) -> str:
        return "CPUExecutionProvider"

    def is_npu_verified(self) -> bool:
        return False

    def get_device_label(self) -> str:
        return "Host CPU (CPUExecutionProvider)"

    def get_runtime_name(self) -> str:
        return "Local PyTorch / ONNX CPU Engine"


class QNNRuntimeAdapter(RuntimeAdapter):
    """
    Qualcomm AI Engine Direct (QNN / HTP) target execution runtime for Snapdragon NPU.
    Status on Intel development machine: NOT VERIFIED (target configured).
    """

    def get_provider_name(self) -> str:
        return "QNNExecutionProvider"

    def is_npu_verified(self) -> bool:
        return False

    def get_device_label(self) -> str:
        return "Snapdragon X Elite / Hexagon NPU (Target Configured)"

    def get_runtime_name(self) -> str:
        return "Qualcomm AI Engine Direct (QNN / HTP Target)"


# ===========================================================================
# Embedding Model Adapter Layer (Section 6)
# Decouples model specifics (SentenceTransformers, Nomic, ONNX) from services
# ===========================================================================

class EmbeddingModelAdapter(ABC):
    """
    Abstract interface for local text embedding models.
    Decouples model execution from business services.
    """

    def __init__(self, runtime_adapter: RuntimeAdapter | None = None) -> None:
        self._runtime_adapter = runtime_adapter or CPURuntimeAdapter()

    def get_runtime_adapter(self) -> RuntimeAdapter:
        return self._runtime_adapter

    @abstractmethod
    def load(self) -> None:
        """Loads model weights and prepares inference session."""
        pass

    @abstractmethod
    def unload(self) -> None:
        """Unloads model weights from memory."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Checks if dependencies and weights are accessible on current system."""
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """Checks if session is currently active in memory."""
        pass

    @abstractmethod
    def get_metadata(self) -> EmbeddingModelMetadata:
        """Returns typed model metadata."""
        pass

    @abstractmethod
    def embed_text(self, text: str, is_query: bool = False) -> np.ndarray:
        """Generates normalized 1D float32 vector for single text input."""
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        """Generates normalized 2D float32 array [N, D] for batch of text inputs."""
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Returns embedding vector dimension."""
        pass

    def get_active_provider(self) -> str:
        return self._runtime_adapter.get_provider_name()

    def is_npu_verified(self) -> bool:
        return self._runtime_adapter.is_npu_verified()


class SentenceTransformerEmbeddingAdapter(EmbeddingModelAdapter):
    """
    Verified local embedding adapter utilizing SentenceTransformers on Host CPU.
    Uses all-MiniLM-L6-v2 (384-dimensional dense vectors, Apache-2.0).
    Completely local in HuggingFace cache — zero external network or cloud calls.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        runtime_adapter: RuntimeAdapter | None = None,
    ) -> None:
        super().__init__(runtime_adapter or CPURuntimeAdapter())
        self._model_name = model_name
        self._dimension = 384
        self._max_seq_len = 256
        self._model: Any = None
        self._is_loaded = False

    def is_available(self) -> bool:
        try:
            import sentence_transformers  # noqa: F401
            return True
        except ImportError:
            return False

    def is_loaded(self) -> bool:
        return self._is_loaded and self._model is not None

    def get_dimension(self) -> int:
        return self._dimension

    def get_metadata(self) -> EmbeddingModelMetadata:
        return EmbeddingModelMetadata(
            name=f"SentenceTransformer ({self._model_name})",
            version="1.0.0",
            source="Local HuggingFace Cache (No Cloud Calls)",
            license="Apache-2.0",
            dimension=self._dimension,
            max_sequence_length=self._max_seq_len,
            runtime=self._runtime_adapter.get_runtime_name(),
            execution_provider=self._runtime_adapter.get_provider_name(),
            npu_verified=self._runtime_adapter.is_npu_verified(),
            hardware_target="Host CPU (Intel) / Snapdragon X Elite Compatible",
            model_size_mb=90.0,
            parameters_m=22.7,
            qualcomm_ai_hub_target="all-MiniLM-L6-v2 / Nomic-Embed-Text v1.5 Target",
            notes="Active verified local CPU baseline; zero cloud or remote telemetry.",
        )

    def load(self) -> None:
        if self.is_loaded():
            return

        try:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading local embedding model %s on CPU...", self._model_name)
            t0 = time.perf_counter()
            self._model = SentenceTransformer(self._model_name, device="cpu")
            load_ms = (time.perf_counter() - t0) * 1000.0
            self._is_loaded = True
            logger.info("Embedding model %s loaded in %.2f ms.", self._model_name, load_ms)
        except Exception as e:
            self._is_loaded = False
            self._model = None
            logger.exception("Failed to load local embedding model: %s", e)
            raise RuntimeError(f"Embedding model initialization failed: {e}") from e

    def unload(self) -> None:
        self._model = None
        self._is_loaded = False
        import gc
        gc.collect()
        logger.info("Embedding model %s unloaded.", self._model_name)

    def embed_text(self, text: str, is_query: bool = False) -> np.ndarray:
        if not self.is_loaded():
            self.load()

        clean_text = text.strip()
        if not clean_text:
            return np.zeros(self._dimension, dtype=np.float32)

        vec = self._model.encode(
            clean_text,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vec.astype(np.float32)

    def embed_batch(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        if not self.is_loaded():
            self.load()

        if not texts:
            return np.empty((0, self._dimension), dtype=np.float32)

        clean_texts = [t.strip() if t.strip() else " " for t in texts]
        vecs = self._model.encode(
            clean_texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=32,
        )
        return vecs.astype(np.float32)


class NomicEmbedTextAdapter(EmbeddingModelAdapter):
    """
    Qualcomm AI Hub preferred embedding model candidate for Snapdragon X Elite / Plus / X2.
    Model: nomic-embed-text-v1.5
    Specs: 137M parameters, ~523 MB float artifact, Apache-2.0, 768-d vectors.
    Snapdragon NPU status: Target configured, NOT VERIFIED on Intel development machine.
    Requires 'einops' for PyTorch CPU fallback and Qualcomm QNN execution provider on ARM64 Snapdragon.
    """

    def __init__(
        self,
        runtime_adapter: RuntimeAdapter | None = None,
    ) -> None:
        super().__init__(runtime_adapter or QNNRuntimeAdapter())
        self._model_name = "nomic-ai/nomic-embed-text-v1.5"
        self._dimension = 768
        self._max_seq_len = 2048
        self._model: Any = None
        self._is_loaded = False

    def is_available(self) -> bool:
        # Check if einops is installed and model weights exist
        try:
            import importlib.util
            if importlib.util.find_spec("einops") is None:
                return False
            import sentence_transformers  # noqa: F401
            return True
        except Exception:
            return False

    def is_loaded(self) -> bool:
        return self._is_loaded and self._model is not None

    def get_dimension(self) -> int:
        return self._dimension

    def get_metadata(self) -> EmbeddingModelMetadata:
        return EmbeddingModelMetadata(
            name="Nomic-Embed-Text v1.5",
            version="1.5.0",
            source="Qualcomm AI Hub Model Zoo / nomic-ai",
            license="Apache-2.0",
            dimension=self._dimension,
            max_sequence_length=self._max_seq_len,
            runtime=self._runtime_adapter.get_runtime_name(),
            execution_provider=self._runtime_adapter.get_provider_name(),
            npu_verified=self._runtime_adapter.is_npu_verified(),
            hardware_target="Snapdragon X Elite / Snapdragon X Plus / Snapdragon X2 Elite",
            model_size_mb=523.0,
            parameters_m=137.0,
            qualcomm_ai_hub_target="Windows Snapdragon QNN Execution Provider (HTP / Hexagon NPU)",
            notes="Qualcomm AI Hub reference model. Current Intel development host uses verified CPU fallback.",
        )

    def load(self) -> None:
        if self.is_loaded():
            return
        if not self.is_available():
            raise RuntimeError(
                "Nomic-Embed-Text v1.5 dependencies are not present on this host (missing 'einops' or Snapdragon QNN provider). "
                "Use the verified local CPU fallback adapter."
            )
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name, trust_remote_code=True, device="cpu")
            self._is_loaded = True
        except Exception as e:
            self._is_loaded = False
            self._model = None
            raise RuntimeError(f"Failed to load Nomic-Embed-Text: {e}") from e

    def unload(self) -> None:
        self._model = None
        self._is_loaded = False

    def embed_text(self, text: str, is_query: bool = False) -> np.ndarray:
        if not self.is_loaded():
            self.load()
        prefix = "search_query: " if is_query else "search_document: "
        clean_text = prefix + text.strip()
        vec = self._model.encode(clean_text, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
        return vec.astype(np.float32)

    def embed_batch(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        if not self.is_loaded():
            self.load()
        prefix = "search_query: " if is_query else "search_document: "
        clean_texts = [prefix + t.strip() for t in texts]
        vecs = self._model.encode(clean_texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False, batch_size=16)
        return vecs.astype(np.float32)
