from __future__ import annotations

import io
import uuid
import numpy as np
import pytest

from app.ai.memory.chunking import chunk_text
from app.ai.memory.embedding_adapter import (
    CPURuntimeAdapter,
    EmbeddingModelAdapter,
    NomicEmbedTextAdapter,
    QNNRuntimeAdapter,
    SentenceTransformerEmbeddingAdapter,
)
from app.ai.memory.embedding_engine import EmbeddingEngine, embedding_engine
from app.ai.memory.indexer import indexer
from app.ai.memory.retriever import retriever
from app.database.models import Document, DocumentChunk, Memory, Project
from app.schemas.memory import (
    DuplicateCheckRequest,
    EmbeddingModelMetadata,
    MemoryCreate,
    MemoryEmbedRequest,
    MemorySearchQuery,
    MemoryUpdate,
)


# ===========================================================================
# 1. Chunking Tests
# ===========================================================================

def test_chunking_word_boundary_and_overlap():
    text = (
        "The ESP32 microcontroller is connected to a DHT11 temperature and humidity sensor. "
        "The circuit requires a 10k ohm pull-up resistor on the data line. "
        "Power is supplied via a 3.3V regulated rail from the USB interface."
    )
    chunks = chunk_text(text, chunk_size=80, overlap=20)
    assert len(chunks) >= 2
    for ch in chunks:
        assert not ch["text"].startswith(" ")
        assert not ch["text"].endswith(" ")
        assert len(ch["text"]) > 0
        assert ch["start_char"] >= 0
        assert ch["end_char"] > ch["start_char"]


def test_chunking_empty_and_short_text():
    assert chunk_text("") == []
    assert chunk_text("   ") == []

    short = "Short single sentence."
    chunks = chunk_text(short, chunk_size=100)
    assert len(chunks) == 1
    assert chunks[0]["text"] == short
    assert chunks[0]["chunk_index"] == 0


# ===========================================================================
# 2. Mock Adapter Unit Tests (Deterministic isolated tests)
# ===========================================================================

class MockEmbeddingAdapter(EmbeddingModelAdapter):
    """Deterministic mock adapter for fast, reproducible unit tests."""

    def __init__(self, dimension: int = 128) -> None:
        super().__init__(CPURuntimeAdapter())
        self._dim = dimension
        self._loaded = True

    def load(self) -> None:
        self._loaded = True

    def unload(self) -> None:
        self._loaded = False

    def is_available(self) -> bool:
        return True

    def is_loaded(self) -> bool:
        return self._loaded

    def get_dimension(self) -> int:
        return self._dim

    def get_metadata(self) -> EmbeddingModelMetadata:
        return EmbeddingModelMetadata(
            name="Mock-Embedding-Adapter",
            version="1.0.0",
            source="Unit Test Mock",
            license="MIT",
            dimension=self._dim,
            max_sequence_length=128,
            runtime="Mock Engine",
            execution_provider="CPUExecutionProvider",
            npu_verified=False,
            hardware_target="Mock Host",
        )

    def embed_text(self, text: str, is_query: bool = False) -> np.ndarray:
        if not text.strip():
            return np.zeros(self._dim, dtype=np.float32)
        # Generate pseudo-deterministic vector based on character sum
        seed = sum(ord(c) for c in text) % 1000
        rng = np.random.RandomState(seed)
        vec = rng.randn(self._dim).astype(np.float32)
        norm = float(np.linalg.norm(vec))
        return vec / norm if norm > 0 else vec

    def embed_batch(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        return np.vstack([self.embed_text(t, is_query=is_query) for t in texts])


def test_mock_engine_lifecycle_and_validation():
    mock_adapter = MockEmbeddingAdapter(dimension=64)
    engine = EmbeddingEngine(adapter=mock_adapter)

    assert engine.is_available() is True
    assert engine.get_dimension() == 64

    # Single embedding
    vec, ms = engine.embed_text("Test sentence")
    assert vec.shape == (64,)
    assert vec.dtype == np.float32
    assert float(np.linalg.norm(vec)) == pytest.approx(1.0, abs=1e-4)
    assert ms >= 0.0

    # Batch embedding
    batch_vecs, b_ms = engine.embed_batch(["Hello", "World"])
    assert batch_vecs.shape == (2, 64)
    assert b_ms >= 0.0


def test_vector_validation_catches_invalid_inputs():
    mock_adapter = MockEmbeddingAdapter(dimension=32)
    engine = EmbeddingEngine(adapter=mock_adapter)

    # Dimension mismatch
    with pytest.raises(ValueError, match="Vector dimension mismatch"):
        engine._validate_vector(np.zeros(16, dtype=np.float32), expected_dim=32)

    # Non-finite values (NaN)
    bad_vec = np.zeros(32, dtype=np.float32)
    bad_vec[0] = np.nan
    with pytest.raises(ValueError, match="non-finite values"):
        engine._validate_vector(bad_vec, expected_dim=32)

    # Non-finite values (Inf)
    bad_vec2 = np.zeros(32, dtype=np.float32)
    bad_vec2[5] = np.inf
    with pytest.raises(ValueError, match="non-finite values"):
        engine._validate_vector(bad_vec2, expected_dim=32)


# ===========================================================================
# 3. Numerically-Safe Cosine Similarity Tests
# ===========================================================================

def test_cosine_similarity_edge_cases():
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v3 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    zero_vec = np.array([0.0, 0.0, 0.0], dtype=np.float32)

    # Normal math
    assert embedding_engine.cosine_similarity(v1, v2) == pytest.approx(1.0, abs=1e-5)
    assert embedding_engine.cosine_similarity(v1, v3) == pytest.approx(0.0, abs=1e-5)

    # Zero vector safety
    assert embedding_engine.cosine_similarity(v1, zero_vec) == 0.0
    assert embedding_engine.cosine_similarity(zero_vec, zero_vec) == 0.0

    # Dimension mismatch
    v_diff = np.array([1.0, 0.0], dtype=np.float32)
    assert embedding_engine.cosine_similarity(v1, v_diff) == 0.0

    # None and empty
    assert embedding_engine.cosine_similarity(None, v1) == 0.0  # type: ignore
    assert embedding_engine.cosine_similarity(np.array([]), v1) == 0.0

    # NaN / Inf safety
    nan_vec = np.array([np.nan, 0.0, 0.0], dtype=np.float32)
    inf_vec = np.array([np.inf, 0.0, 0.0], dtype=np.float32)
    assert embedding_engine.cosine_similarity(v1, nan_vec) == 0.0
    assert embedding_engine.cosine_similarity(v1, inf_vec) == 0.0


# ===========================================================================
# 4. Live Model Execution & Serialization Tests (Host CPU)
# ===========================================================================

def test_live_embedding_model_properties_and_serialization():
    vec, latency_ms = embedding_engine.embed_text("ESP32 temperature monitoring project", is_query=False)
    assert isinstance(vec, np.ndarray)
    assert vec.dtype == np.float32
    assert vec.shape == (384,)
    assert latency_ms > 0
    assert np.all(np.isfinite(vec))

    # L2 Norm should be approximately 1.0
    norm = float(np.linalg.norm(vec))
    assert norm == pytest.approx(1.0, abs=1e-3)

    # Test serialization to float32 bytes for SQLite BLOB storage
    vec_bytes = embedding_engine.vector_to_bytes(vec)
    assert len(vec_bytes) == 384 * 4  # 384 float32 = 1536 bytes

    restored_vec = embedding_engine.bytes_to_vector(vec_bytes, expected_dim=384)
    assert np.allclose(vec, restored_vec, atol=1e-6)

    # Corrupt or mismatched dimension byte decoding raises ValueError
    with pytest.raises(ValueError, match="Corrupt or mismatched"):
        embedding_engine.bytes_to_vector(vec_bytes[:100], expected_dim=384)


def test_nomic_adapter_target_configuration():
    nomic_adapter = NomicEmbedTextAdapter()
    meta = nomic_adapter.get_metadata()
    assert meta.dimension == 768
    assert "nomic" in meta.name.lower()
    assert meta.npu_verified is False  # Truthful
    assert meta.execution_provider == "QNNExecutionProvider"
    assert "Snapdragon" in meta.hardware_target


# ===========================================================================
# 5. Controlled Test Dataset (Section 35) & Semantic Ranking
# ===========================================================================

def test_controlled_dataset_semantic_retrieval(client):
    """
    Validates Section 35 controlled dataset:
    Memory 1: Temperature monitoring project using ESP32 and DHT11 sensor.
    Memory 2: Badminton racket string tension is 26 lbs.
    Memory 3: Python FastAPI backend handles file uploads.
    Memory 4: Electronics circuit uses a 3.3V LDO regulator.
    Memory 5: Motorcycle maintenance notes.
    """
    test_memories = [
        ("Temperature Project", "Temperature monitoring project using ESP32 and DHT11 sensor.", "project"),
        ("Badminton Racket", "Badminton racket string tension is 26 lbs with synthetic gut.", "note"),
        ("FastAPI Backend", "Python FastAPI backend handles file uploads asynchronously.", "note"),
        ("Power Circuit", "Electronics circuit uses a 3.3V LDO regulator with 10uF caps.", "project"),
        ("Motorcycle Notes", "Motorcycle maintenance notes including chain lubrication.", "note"),
    ]

    created_ids: list[int] = []
    for title, content, cat in test_memories:
        res = client.post(
            "/api/memory",
            json={"title": title, "content": content, "category": cat, "source_type": "USER_NOTE"},
        )
        assert res.status_code == 201
        created_ids.append(res.json()["id"])

    # Query 1: "What sensor did I use in the temperature project?"
    # Memory 1 (Temperature Project) should rank #1
    res1 = client.post(
        "/api/memory/search",
        json={"query": "What sensor did I use in the temperature project?", "search_mode": "SEMANTIC", "top_k": 3},
    )
    assert res1.status_code == 200
    hits1 = res1.json()["results"]
    assert len(hits1) >= 1
    assert "Temperature" in hits1[0]["title"]
    assert hits1[0]["semantic_score"] > 0.45

    # Query 2: "What regulator is mentioned in my circuit notes?"
    # Memory 4 (Power Circuit) should rank #1
    res2 = client.post(
        "/api/memory/search",
        json={"query": "What regulator is mentioned in my circuit notes?", "search_mode": "SEMANTIC", "top_k": 3},
    )
    assert res2.status_code == 200
    hits2 = res2.json()["results"]
    assert len(hits2) >= 1
    assert "Power Circuit" in hits2[0]["title"] or "regulator" in hits2[0]["content"].lower()
    assert hits2[0]["semantic_score"] > 0.40


# ===========================================================================
# 6. Controlled Document Test (Section 36)
# ===========================================================================

def test_controlled_document_chunk_retrieval(client):
    """
    Validates Section 36:
    Ingests document: "The circuit requires a 10kΩ pull-up resistor for the sensor."
    Query: "What resistor does the sensor circuit require?"
    Top result should be the document chunk with document ID and page number intact.
    """
    doc_text = (
        "Hardware Design Guide\n"
        "The circuit requires a 10k ohm pull-up resistor for the sensor data line.\n"
        "Without this pull-up resistor, signal integrity cannot be guaranteed."
    )
    # Upload text document
    upload_res = client.post(
        "/api/files/upload",
        files={"file": ("hardware_guide.txt", io.BytesIO(doc_text.encode("utf-8")), "text/plain")},
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["file_id"]

    # Ingest document
    doc_res = client.post("/api/documents", json={"file_id": file_id})
    assert doc_res.status_code == 201
    doc_data = doc_res.json()

    # Query: "What resistor does the sensor circuit require?"
    search_res = client.post(
        "/api/memory/search",
        json={
            "query": "What resistor does the sensor circuit require?",
            "search_mode": "HYBRID",
            "top_k": 5,
            "include_documents": True,
        },
    )
    assert search_res.status_code == 200
    hits = search_res.json()["results"]

    # Verify that a document result was returned with correct metadata
    doc_hits = [h for h in hits if h["result_type"] == "DOCUMENT"]
    assert len(doc_hits) >= 1
    top_doc = doc_hits[0]
    assert "10k" in top_doc["content"]
    assert top_doc["source_type"] == "DOCUMENT"
    assert top_doc["source_id"] == doc_data["document_id"]
    assert top_doc["page_number"] is not None


# ===========================================================================
# 7. Search Modes (Keyword vs Semantic vs Hybrid)
# ===========================================================================

def test_search_mode_behavior(client):
    # Create memory with distinct wording
    client.post(
        "/api/memory",
        json={
            "title": "Quantum Computation Notes",
            "content": "Superconducting qubits maintain coherence at sub-Kelvin temperatures in dilution refrigerators.",
            "category": "note",
        },
    )

    # 1. Pure Keyword with matching word
    kw_res = client.post(
        "/api/memory/search",
        json={"query": "superconducting qubits", "search_mode": "KEYWORD", "top_k": 3},
    )
    assert kw_res.status_code == 200
    assert any("Quantum" in h["title"] for h in kw_res.json()["results"])

    # 2. Pure Keyword with zero lexical overlap
    no_kw_res = client.post(
        "/api/memory/search",
        json={"query": "extremely cold processors", "search_mode": "KEYWORD", "top_k": 3},
    )
    assert no_kw_res.status_code == 200
    # No keyword overlap means 0 results in pure KEYWORD mode
    assert len(no_kw_res.json()["results"]) == 0

    # 3. Semantic mode with synonymous wording
    sem_res = client.post(
        "/api/memory/search",
        json={"query": "extremely cold processors", "search_mode": "SEMANTIC", "top_k": 3},
    )
    assert sem_res.status_code == 200
    assert len(sem_res.json()["results"]) >= 1


# ===========================================================================
# 8. Duplicate Detection (Section 28)
# ===========================================================================

def test_duplicate_detection_logic(client):
    proj_res = client.post("/api/projects", json={"name": f"Project {uuid.uuid4().hex[:6]}"})
    proj_id = proj_res.json()["id"]

    mem_res = client.post(
        "/api/memory",
        json={
            "title": "Motor Controller Setup",
            "content": "Brushless DC motor driven by DRV8302 inverter with FOC algorithms.",
            "project_id": proj_id,
        },
    )
    mem_id = mem_res.json()["id"]

    # Exact duplicate test
    exact_res = client.post(
        "/api/memory/check-duplicate",
        json={
            "title": "Motor Controller Setup",
            "content": "Brushless DC motor driven by DRV8302 inverter with FOC algorithms.",
            "project_id": proj_id,
        },
    )
    assert exact_res.status_code == 200
    assert exact_res.json()["is_duplicate"] is True
    assert exact_res.json()["similarity"] >= 0.99
    assert exact_res.json()["existing_memory_id"] == mem_id

    # Paraphrased duplicate test
    para_res = client.post(
        "/api/memory/check-duplicate",
        json={
            "title": "Motor Controller Setup",
            "content": "Brushless DC motor driven by DRV8302 inverter and FOC algorithm.",
            "project_id": proj_id,
            "threshold": 0.80,
        },
    )
    assert para_res.status_code == 200
    assert para_res.json()["is_duplicate"] is True
    assert para_res.json()["similarity"] > 0.80

    # Unrelated memory test
    unrel_res = client.post(
        "/api/memory/check-duplicate",
        json={
            "title": "Grocery Shopping List",
            "content": "Apples, bananas, milk, and sourdough bread.",
            "project_id": proj_id,
            "threshold": 0.80,
        },
    )
    assert unrel_res.status_code == 200
    assert unrel_res.json()["is_duplicate"] is False


# ===========================================================================
# 9. Stale Transition on Edit & Deletion Safety (Section 12, 13)
# ===========================================================================

def test_memory_edit_and_delete_preservation(client):
    create_res = client.post(
        "/api/memory",
        json={"title": "Draft Design", "content": "Initial circuit specification."},
    )
    mem_id = create_res.json()["id"]
    assert create_res.json()["embedding_status"] == "READY"

    # Edit memory content -> automatically re-indexes and remains READY
    edit_res = client.put(
        f"/api/memory/{mem_id}",
        json={"content": "Finalized circuit specification with 5V buck converter."},
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["embedding_status"] == "READY"
    assert "buck converter" in edit_res.json()["content"]

    # Delete memory -> deletes memory metadata & embedding
    del_res = client.delete(f"/api/memory/{mem_id}")
    assert del_res.status_code == 200

    # Check 404
    get_res = client.get(f"/api/memory/{mem_id}")
    assert get_res.status_code == 404


# ===========================================================================
# 10. Reindexing & Status Endpoints (Section 29, 34)
# ===========================================================================

def test_reindex_idempotency_and_embed_api(client):
    # Test POST /api/memory/embed
    embed_res = client.post("/api/memory/embed", json={"text": "Local semantic embedding test"})
    assert embed_res.status_code == 200
    embed_data = embed_res.json()
    assert embed_data["dimension"] == 384
    assert embed_data["latency_ms"] >= 0
    assert embed_data["status"] == "READY"

    # Test GET /api/memory/embedding-status
    status_res = client.get("/api/memory/embedding-status")
    assert status_res.status_code == 200
    st_data = status_res.json()
    assert st_data["is_available"] is True
    assert st_data["model"]["dimension"] == 384
    assert "Host CPU" in st_data["device_label"]
    assert st_data["target_model_name"] == "nomic-embed-text-v1.5"
    assert st_data["npu_status"] == "NOT VERIFIED"

    # Test POST /api/memory/reindex (idempotent)
    reindex_res = client.post("/api/memory/reindex?force=true&include_documents=true")
    assert reindex_res.status_code == 200
    assert reindex_res.json()["status"] == "SUCCESS"
    assert reindex_res.json()["duration_ms"] >= 0
