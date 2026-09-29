# SENTINEL Vision Models Directory

This directory stores local ONNX model weights and configuration files for SENTINEL's real local vision engine.

## Policy & Safety

- **No Binary Weights in Version Control**: Binary model weights (`*.onnx`, `*.bin`, `*.weights`, `*.pt`) are strictly excluded via `.gitignore` to maintain repository integrity.
- **Explicit Acquisition Only**: Models must be downloaded explicitly through documented procedures. SENTINEL does not silently download multi-gigabyte models in the background.

## Primary Vision Model Candidate: YOLO-X (Qualcomm AI Hub)

SENTINEL's first selected vision model candidate is **YOLO-X** (Nano / Small), following the Qualcomm official Windows Object Detection reference implementation:
- **Reference Sample**: Qualcomm AI Hub Windows C++ / Python Object Detection (`object_detection_windows_cpp`)
- **Format**: ONNX (`yolox.onnx`)
- **Supported EPs**: `QNNExecutionProvider` (Snapdragon Hexagon NPU), `CPUExecutionProvider` (Fallback)
- **License**: Apache 2.0 (Permissive, commercial-friendly)
- **Input Dimensions**: 640x640x3 (RGB normalized)
- **Output**: 80 COCO classes, bounding boxes `[x1, y1, x2, y2]`, detection confidence

### Acquisition Procedure (Phase 2B)

1. **Via Qualcomm AI Hub**:
   ```bash
   # Using Qualcomm AI Hub CLI
   qai-hub compile --model yolox --target-runtime onnx --device "Snapdragon X Elite"
   ```
2. **Via Pre-exported Official ONNX Artifact**:
   Place the downloaded `yolox_nano.onnx` or `yolox_s.onnx` into this directory:
   ```
   models/
   └── vision/
       ├── README.md
       └── yolox.onnx   (not tracked in git)
   ```

3. **Verification**:
   Once placed, SENTINEL's ModelSelector and Vision Pipeline will validate the graph input/output shapes and initialize through the active execution provider (`CPUExecutionProvider` on dev machine, `QNNExecutionProvider` on Snapdragon target).
