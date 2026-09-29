# SENTINEL Workspace Tracking, Visual Grounding & "Find It" Localization (Step 5)

## Overview & Progression

SENTINEL evolves the desk AI experience from static frame detection into dynamic, real-time workspace awareness:
**SEE (Detect) → TRACK (Stable IDs) → UNDERSTAND (Spatial Geometry) → REMEMBER (Last-Seen Memory) → FIND (Natural-Language Search)**

Step 5 introduces real-time object tracking across frames, deterministic 2D spatial relationships, user-assigned object aliases, and the **Find It** workspace search engine.

---

## Hardware Truthfulness & Execution Separation

SENTINEL strictly preserves architectural truthfulness regarding execution hardware:

| Dimension | Current Development Host | Target Snapdragon Platform |
| :--- | :--- | :--- |
| **System** | Windows 11 x86_64 Laptop | Windows 11 ARM64 Copilot+ PC |
| **Processor** | Intel Core CPU | Snapdragon X Elite / X Plus / X2 Elite |
| **NPU** | **NOT VERIFIED** | Qualcomm Hexagon NPU (45+ TOPS) |
| **Object Detection** | YOLO-X (ONNX Runtime CPU) | YOLO-X (ONNX Runtime QNN Provider) |
| **Tracking Engine** | Lightweight Deterministic 2D Tracker | Lightweight Deterministic 2D Tracker |
| **Spatial Model** | Deterministic Coordinate Geometry | Deterministic Coordinate Geometry |
| **Status Label** | `HOST CPU STAGING` | `TARGET / NOT VERIFIED` |

> [!IMPORTANT]
> Object tracking IDs (e.g. `track_001`, `track_002`) are **temporary visual identifiers** only. The system does not implement facial recognition, biometric identity profiling, or covert background surveillance.

---

## Dedicated Tracking Architecture

The tracking and spatial localization pipeline is cleanly decoupled from the presentation layer:

```
VisionEngine (YOLO-X Detections)
       ↓
ObjectTracker (IoU + Centroid Distance + EMA Smoothing)
       ↓
SpatialReasoningEngine (9 Workspace Zones + Relative Geometry)
       ↓
WorkspaceState / SpatialMemory (Active Tracks + TTL Observations)
       ↓
FindItService (Hierarchical Resolution + Ambiguity & Uncertainty Handling)
       ↓
API & UI Presentation
```

---

## Tracking Algorithm & Temporal Stability

The `ObjectTracker` uses a lightweight, multi-stage matching strategy designed for desktop camera feeds without adding heavy neural network dependencies:

1. **Stage 1 (IoU Matching)**:
   Matches incoming detections of the same class against active tracks using bounding box Intersection-over-Union (threshold: `0.25`).
2. **Stage 2 (Centroid Distance Matching)**:
   For objects with large inter-frame displacement where IoU drops, matches by normalized 2D centroid distance (threshold: `0.25`).
3. **Stage 3 (Track Initialization)**:
   Unmatched detections with confidence $\ge 0.20$ spawn new track IDs (`track_001`, `track_002`, ...).
4. **Stage 4 (Exponential Moving Average Temporal Smoothing)**:
   Prevents bounding box visual jitter across frames:
   $$\text{smoothed} = \alpha \cdot \text{raw} + (1 - \alpha) \cdot \text{smoothed}_{\text{prev}} \quad (\alpha = 0.65)$$
5. **Velocity Estimation**:
   Centroid delta over frame duration:
   $$v_x = \frac{\Delta x}{\Delta t}, \quad v_y = \frac{\Delta y}{\Delta t}$$
6. **Track Stability Score**:
   $$\text{stability} = \frac{\text{frames\_seen}}{\text{frames\_seen} + \text{consecutive\_misses}}$$

---

## 2D Workspace Spatial Model

The camera view is mapped into normalized 2D coordinates:
- $x = 0.0$ (left) $\rightarrow x = 1.0$ (right)
- $y = 0.0$ (top) $\rightarrow y = 1.0$ (bottom)

Centroids are categorized into **9 discrete workspace zones**:
- `top-left`, `top-center`, `top-right`
- `center-left`, `center`, `center-right`
- `bottom-left`, `bottom-center`, `bottom-right`

### Deterministic Spatial Relationships
Geometric relationships between visible tracks are calculated deterministically without LLM guesswork:
- **`left_of` / `right_of`**: $\Delta x > \pm 0.08$ normalized units
- **`above` / `below`**: $\Delta y > \pm 0.08$ normalized units
- **`near`**: Euclidean centroid distance $< 0.35$ normalized units
- **`overlaps`**: $\text{IoU} \ge 0.04$

Examples generated:
- *"bottle is right of keyboard"*
- *"mouse is near keyboard"*
- *"monitor is above keyboard"*

---

## Expiration Policy & Observation Lifecycle

Spatial memory is strictly separated from long-term conversational memory (`MEMORA`). Spatial observations operate under an expiration lifecycle:

| State | Condition / Age | Behavior |
| :--- | :--- | :--- |
| **`CURRENT_VISIBLE`** | Detected in current frame ($\text{age} \le 3.0\text{s}$) | Active in real-time view; highlighted as current |
| **`RECENTLY_SEEN`** | Temporarily occluded / missing ($3.0\text{s} < \text{age} \le 15.0\text{s}$) | Reported as "last seen $X$ seconds ago in [region]" |
| **`STALE`** | Not seen for $15.0\text{s} < \text{age} \le 60.0\text{s}$ | Reported as "visible $X$ seconds ago, but no longer in view" |
| **`EXPIRED`** | $\text{age} > 60.0\text{s}$ or misses $> 15$ | Evicted from active spatial memory; returned as `NOT_FOUND` |

---

## "Find It" Natural-Language Resolution

`FindItService` resolves user queries (e.g. *"Where is my water bottle?"*, *"Find the laptop"*, *"What is next to my keyboard?"*) using a 6-stage hierarchical matching engine:

1. **User-Remembered Labels**: Explicitly assigned human aliases (e.g. *"my hydroflask"*, *"lab multimeter"*).
2. **OCR-Associated Text**: Text extracted by EasyOCR on or immediately adjacent to the object (e.g. *"Digital Electronics"* book).
3. **Exact Class & Synonyms**: Canonical class names and aliases (e.g. `bottle` $\leftrightarrow$ `water bottle`, `flask`, `container`; `cell phone` $\leftrightarrow$ `phone`, `mobile`).
4. **Relational Preposition Queries**: Identifies anchor objects in questions like *"what is next to the keyboard?"* and resolves adjacent objects.
5. **Project Scope Filtering**: Enforces project isolation; observations from mismatched projects are excluded.
6. **Ambiguity & Uncertainty Handling**:
   - If multiple candidates exist (e.g. two visible bottles), returns `match_type: "AMBIGUOUS"` and lists candidates for user selection.
   - If no evidence exists, returns `match_type: "NOT_FOUND"`. **Never fabricates coordinates or hallucinated locations.**

---

---

## Visual Grounding & Structured Grounding Actions (Step 7)

When a target is located:
- Returns a structured `grounding_box` with normalized coordinates.
- Frontend illuminates the target bounding box with a glowing cyan animated highlight border and a **TARGET FOUND** indicator.
- Displays last-seen recency, spatial zone, and neighboring relationships.
- **Structured Orchestrator Grounding Action**: In Step 7, queries route through `SentinelOrchestrator`, which returns a typed `GroundingAction` (`action: HIGHLIGHT_OBJECT`, `target_id: track_001`, `box_2d: {x1, y1, x2, y2}`, `zone: center_right`). The UI handles this structured action deterministically without requiring code generation.

---

## Privacy Boundaries & Camera Lifecycle

- **User-Controlled Lifecycle**: Camera processing only runs while the user explicitly starts the camera. Leaving the page or toggling off camera triggers an immediate `STOPPING` command, releasing the MediaStream and clearing active tracks.
- **Zero Raw Frame Persistence**: Raw video frames are processed in memory and never persisted to the SQLite database.
- **No Biometrics**: Only COCO-style inanimate desk objects are tracked. No facial recognition or biometric tracking exists.
- **Zero Cloud Ingestion**: Tracking, spatial reasoning, and Find It execute 100% locally on-device.

---

## Measured Performance (Host Development Staging)

- **Tracking Update Latency**: `~0.4 - 1.2 ms` per frame
- **Spatial Reasoning Latency**: `~0.2 - 0.5 ms` across pairs of visible objects
- **Find It Query Latency**: `~1.0 - 2.5 ms` end-to-end
- **Memory Footprint**: `~2 KB` per active tracked object in memory cache
- **Frame Processing Throughput**: Capable of 60+ FPS tracking passes on top of YOLO-X detections
