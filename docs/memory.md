# MEMORA — Local Semantic Memory & Hybrid Retrieval Engine

## 1. Product Purpose & Architectural Principles

SENTINEL's core vision is:
> **"Your private AI that sees, reads, remembers, understands, and eventually helps you find things."**

The architectural progression unfolds across distinct capability stages:
```
SEE (YOLO-X Object Detection)
  → READ (EasyOCR CRAFT + CRNN Text Extraction)
    → REMEMBER (MEMORA Local Semantic Memory & Vector Storage)
      → UNDERSTAND (Multimodal Reasoning Engine)
        → FIND (Unified Cross-Modal Retrieval)
```

In Step 3, SENTINEL implements **MEMORA: Real Local Semantic Memory & Hybrid Retrieval**.

### Absolute Privacy Rule: Persistent Memory vs Source Data
Persistent memory remains **strictly and explicitly user-controlled**:
- **Persistent Personal Memory:** Information the user intentionally chose to preserve (e.g., clicking "Add Memory", "Remember this", "Save to project").
- **Searchable Source Data:** Extracted PDF chunks, OCR text boxes, conversation transcripts, and raw images available for semantic retrieval **without being automatically promoted to personal memories**.
- **No Automatic Memorization:** Conversations, camera observations, OCR results, and uploaded files are never converted into personal user memories without explicit user action.
- **Zero Cloud Dependence:** Vector embeddings are generated entirely locally via on-device neural runtimes. Zero data ever leaves the local device.

---

## 2. Decoupled Model Adapter Architecture

To ensure the memory architecture is completely hardware-portable, a decoupled 4-tier layer pattern is implemented:

```
MemoryService (Business Logic, CRUD, Duplicate Guard)
      ↓
EmbeddingEngine (Thread-Safe Lifecycle, Vector Validation, Math Safety)
      ↓
EmbeddingModelAdapter (Model-Specific Tokenization, Preprocessing & Pooling)
      ↓
RuntimeAdapter (Hardware Provider: Host CPU vs Qualcomm QNN/NPU)
      ↓
Hardware Accelerator (Host Intel CPU vs Snapdragon X Elite Hexagon NPU)
```

1. **`RuntimeAdapter` (Abstract Base Class):**
   - `CPURuntimeAdapter`: Executes on Host CPU using `CPUExecutionProvider` (Verified on Intel Development Host).
   - `QNNRuntimeAdapter`: Target execution runtime using `QNNExecutionProvider` targeting Qualcomm Hexagon NPU on Snapdragon X Elite / Plus / X2. Status on Intel machine: **NOT VERIFIED (Target Configured)**.
2. **`EmbeddingModelAdapter` (Abstract Base Class):**
   - Decouples embedding model specifics (dimensions, sequence length, input prefixes) from business services.
   - `SentenceTransformerEmbeddingAdapter`: Active verified local CPU baseline using `all-MiniLM-L6-v2` (384-dimensional dense vectors, Apache-2.0, cached locally).
   - `NomicEmbedTextAdapter`: Qualcomm AI Hub target model candidate using `nomic-embed-text-v1.5` (768-dimensional vectors, 137M parameters, 523 MB float artifact, Apache-2.0).
3. **`EmbeddingEngine`:**
   - Thread-safe manager enforcing vector validation (`ndim == 1`, exact expected dimension, strictly finite values, no NaN/Inf).
   - Float32 binary byte serialization/deserialization for SQLite BLOB storage.
   - Numerically-safe cosine similarity computation.

---

## 3. Embedding Model Strategy & Truthful Status

### Qualcomm Reference Model Target
- **Model Name:** Nomic-Embed-Text v1.5 (`nomic-ai/nomic-embed-text-v1.5`)
- **Parameter Count:** 137 Million
- **Model Artifact Size:** ~523 MB Float
- **License:** Apache-2.0
- **Qualcomm AI Hub Target Platform:** Snapdragon X Elite, Snapdragon X Plus 8-Core, Snapdragon X2 Elite
- **Target Runtime:** Windows on Snapdragon via QNN Execution Provider (HTP / Hexagon NPU)
- **Status on Intel Host:** Target configured in `NomicEmbedTextAdapter`. Exact remaining dependencies for local CPU execution: `einops` package and Qualcomm QNN execution provider on ARM64 Snapdragon.

### Active Verified Local Host CPU Baseline
- **Model Name:** SentenceTransformer (`all-MiniLM-L6-v2`)
- **Embedding Dimension:** 384
- **Parameters:** 22.7 Million (~90 MB)
- **License:** Apache-2.0
- **Execution Provider:** `CPUExecutionProvider` on Host CPU
- **Network Access:** Zero external calls — 100% offline from local cache.
- **Snapdragon NPU Status:** **NOT VERIFIED** (Truthfully reported across API and AI Lab).

---

## 4. Local Vector Storage & Database Schema

SENTINEL stores embedding vectors directly inside local SQLite database records as `float32` binary blobs (`LargeBinary` / SQLite `BLOB`):

### SQLite Schema Extensions
```sql
-- Memory Table (Personal Intentional Memories)
ALTER TABLE memories ADD COLUMN embedding BLOB;
ALTER TABLE memories ADD COLUMN embedding_status VARCHAR(20) DEFAULT 'PENDING';
ALTER TABLE memories ADD COLUMN embedding_model VARCHAR(100);
ALTER TABLE memories ADD COLUMN embedding_model_version VARCHAR(50);
ALTER TABLE memories ADD COLUMN embedding_dimension INTEGER;

-- Document Chunks Table (Searchable Source Data)
CREATE TABLE document_chunks (
    id INTEGER PRIMARY KEY,
    document_id VARCHAR(64) REFERENCES documents(document_id) ON DELETE CASCADE,
    page_number INTEGER DEFAULT 1,
    chunk_index INTEGER DEFAULT 0,
    text_content TEXT NOT NULL,
    embedding BLOB,
    embedding_status VARCHAR(20) DEFAULT 'READY',
    embedding_model VARCHAR(100),
    embedding_model_version VARCHAR(50),
    embedding_dimension INTEGER,
    start_char INTEGER DEFAULT 0,
    end_char INTEGER DEFAULT 0,
    created_at TIMESTAMP
);
```

### Float32 Binary Serialization
- Encoding: `vec.astype(np.float32).tobytes()` (384 float32 = 1,536 bytes; 768 float32 = 3,072 bytes).
- Decoding: `np.frombuffer(b, dtype=np.float32)`.
- Dimension and finite integrity validation occurs before any cosine similarity comparison.

---

## 5. Chunking Strategy

Implemented in `backend/app/ai/memory/chunking.py`:
- **Word-Boundary Preservation:** Regex sentence segmentation ensures words are never severed mid-token.
- **Target Chunk Size:** 450 characters (~100 tokens, configurable).
- **Contiguous Overlap:** 50 characters (preserves sentence continuity across chunk boundaries).
- **Contextual Formatting:** Includes document file name and page number for enhanced semantic recall.

---

## 6. Numerically-Safe Cosine Similarity

Implemented in `EmbeddingEngine.cosine_similarity(vec1, vec2)`:
$$\text{Cosine}(A, B) = \frac{A \cdot B}{\|A\|_2 \cdot \|B\|_2}$$
Edge-case safety guarantees:
- Returns `0.0` if either vector is `None`, empty, or dimension-mismatched.
- Returns `0.0` if either vector has an $L_2$ norm $\le 10^{-12}$ (zero vectors).
- Returns `0.0` if any element is non-finite (`NaN` or `Infinity`).
- Clamped strictly to $[0.0, 1.0]$.

---

## 7. Hybrid Search Scoring Formula

SENTINEL implements hybrid retrieval combining semantic similarity, lexical keyword matching, and metadata context:

$$\text{Score}_{\text{hybrid}} = \frac{w_s \cdot S_{\text{semantic}} + w_k \cdot S_{\text{keyword}} + w_m \cdot S_{\text{metadata}}}{\max(10^{-4}, w_s + w_k + w_m)}$$

Where:
- $S_{\text{semantic}} \in [0.0, 1.0]$: Cosine similarity between query embedding and candidate vector.
- $S_{\text{keyword}} \in [0.0, 1.0]$: Lexical token containment ratio:
  $$S_{\text{keyword}} = \frac{|\{t \in T_{\text{query}} : t \text{ is in } \text{Text}\}|}{|T_{\text{query}}|}$$
  with $+0.2$ bonus for exact phrase matching.
- $S_{\text{metadata}} \in [0.0, 1.0]$: Metadata relevance bonus ($+0.5$ for matching project ID, $+0.3$ for high importance).
- **Default Weights:** $w_s = 0.65$ (Semantic), $w_k = 0.25$ (Keyword), $w_m = 0.10$ (Metadata).
- **Search Modes:**
  - `HYBRID`: Combined weighted score.
  - `SEMANTIC`: Pure cosine similarity ($S_{\text{semantic}}$).
  - `KEYWORD`: Pure lexical overlap ($S_{\text{keyword}}$).

---

## 8. Memory Lifecycle & Duplicate Detection

1. **Creation:** `PENDING` $\to$ `EmbeddingEngine` $\to$ vector stored $\to$ `READY`. (If embedding fails, status is `FAILED`; memory is never discarded).
2. **Editing:** Content modification transitions status to `STALE` $\to$ re-indexes $\to$ `READY`.
3. **Deletion:** Deleting a memory removes its metadata and vector without affecting source documents or projects.
4. **Duplicate Detection:**
   - Evaluates exact normalized text match (similarity $= 1.0$) and semantic cosine similarity.
   - If similarity $\ge 0.85$, user is prompted with options: **Keep Both (Save Anyway)** or **Cancel**.

---

## 9. Measured Host CPU Performance Baseline

Measured live on Intel Core CPU development host:

| Metric | Measured Host CPU Value | Notes |
|---|---|---|
| **Embedding Model Cold Load** | `5,277.14 ms` | Initial PyTorch CPU load |
| **Single Text Embedding Latency** | `16.41 ms` | Mean of 5 inferences (`all-MiniLM-L6-v2`) |
| **Query Embedding Latency** | `7.89 ms` | Mean of 5 short queries |
| **Batch Embedding Latency (5 items)** | `18.31 ms` | Batch throughput: **273.1 items/sec** |
| **Keyword Search Latency** | `34.32 ms` | Full tokenization and substring scan |
| **Semantic Vector Search Latency** | `2.24 ms` | Vector similarity scan (`10.29 ms` total incl. query embed) |
| **Hybrid Retrieval Latency** | `3.24 ms` | Combined scoring (`10.47 ms` total incl. query embed) |
| **Memory Footprint** | `< 120 MB` | Lean on-device working set |

*Note: All figures represent Host Intel CPU execution. Snapdragon X Elite NPU benchmark data will be collected upon deployment to target Qualcomm hardware.*
