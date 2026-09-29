from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, model_validator


class BoundingBox(BaseModel):
    x: float = Field(default=0.0, description="Normalized top-left X coordinate [0.0 - 1.0]")
    y: float = Field(default=0.0, description="Normalized top-left Y coordinate [0.0 - 1.0]")
    width: float = Field(default=0.0, description="Normalized width [0.0 - 1.0]")
    height: float = Field(default=0.0, description="Normalized height [0.0 - 1.0]")
    x_min: float = Field(default=0.0, description="Normalized top-left X coordinate [0.0 - 1.0]")
    y_min: float = Field(default=0.0, description="Normalized top-left Y coordinate [0.0 - 1.0]")
    x_max: float = Field(default=0.0, description="Normalized bottom-right X coordinate [0.0 - 1.0]")
    y_max: float = Field(default=0.0, description="Normalized bottom-right Y coordinate [0.0 - 1.0]")
    x_abs_min: float | None = Field(default=None, description="Absolute pixel top-left X in original image")
    y_abs_min: float | None = Field(default=None, description="Absolute pixel top-left Y in original image")
    x_abs_max: float | None = Field(default=None, description="Absolute pixel bottom-right X in original image")
    y_abs_max: float | None = Field(default=None, description="Absolute pixel bottom-right Y in original image")

    @model_validator(mode="before")
    @classmethod
    def sync_coordinates(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "x_min" in data and "x" not in data:
                data["x"] = data["x_min"]
            if "y_min" in data and "y" not in data:
                data["y"] = data["y_min"]
            if "x_min" in data and "x_max" in data and "width" not in data:
                data["width"] = round(max(0.0, data["x_max"] - data["x_min"]), 4)
            if "y_min" in data and "y_max" in data and "height" not in data:
                data["height"] = round(max(0.0, data["y_max"] - data["y_min"]), 4)
            if "x" in data and "x_min" not in data:
                data["x_min"] = data["x"]
            if "y" in data and "y_min" not in data:
                data["y_min"] = data["y"]
            if "x" in data and "width" in data and "x_max" not in data:
                data["x_max"] = round(data["x"] + data["width"], 4)
            if "y" in data and "height" in data and "y_max" not in data:
                data["y_max"] = round(data["y"] + data["height"], 4)
        return data


class Detection(BaseModel):
    class_id: int = Field(..., description="Class index from model ontology")
    label: str = Field(..., description="Human readable label")
    confidence: float = Field(..., description="Confidence score [0.0 - 1.0]")
    bbox: BoundingBox = Field(..., description="Bounding box coordinates")


class OCRResult(BaseModel):
    text: str = Field(..., description="Extracted text string")
    confidence: float = Field(default=1.0, description="Confidence score [0.0 - 1.0]")
    bbox: BoundingBox | None = Field(default=None, description="Bounding box coordinates for detected text")
    line_number: int | None = Field(default=None, description="Sequence line number")


class TimingMetrics(BaseModel):
    preprocess_ms: float = Field(..., description="Image load, resize, and letterbox time in ms")
    inference_ms: float = Field(..., description="Raw model execution pass in ms")
    postprocess_ms: float = Field(..., description="NMS, thresholding, and coordinate mapping in ms")
    total_ms: float = Field(..., description="Total pipeline latency in ms")


class ImageMetadata(BaseModel):
    original_width: int
    original_height: int
    channels: int = 3
    aspect_ratio: str


class ModelInferenceMetadata(BaseModel):
    name: str = "YOLO-X"
    version: str = "Small"
    source: str = "Qualcomm AI Hub Official Reference"
    license: str = "Apache-2.0"
    format: str = "ONNX"
    input_shape: list[int] = Field(default_factory=lambda: [1, 3, 640, 640])
    model_size_mb: float | None = None


class RuntimeVerificationMetadata(BaseModel):
    execution_provider: str
    npu_verified: bool = False
    verification_method: str = "NOT_TESTED"
    display_label: str = "LOCAL • CPU"


class VisionAnalyzeRequest(BaseModel):
    file_id: str | None = Field(default=None, description="ID of previously uploaded file to analyze")
    image: str | None = Field(default=None, description="Base64 encoded frame or image payload")
    prompt: str | None = Field(default=None, description="Optional reasoning or grounding query")
    confidence_threshold: float = Field(default=0.25, ge=0.01, le=1.0, description="Minimum confidence threshold")
    iou_threshold: float = Field(default=0.45, ge=0.01, le=1.0, description="Non-maximum suppression IoU threshold")


class VisionResult(BaseModel):
    status: str = Field(default="READY", description="Inference status code")
    message: str = Field(..., description="Status description")
    objects: list[Detection] = Field(default_factory=list, description="Detected objects")
    ocr: list[OCRResult] = Field(default_factory=list, description="Extracted OCR text blocks")
    scene: str = Field(default="", description="Scene description or classification")
    detected_count: int = Field(default=0, description="Total count of detected entities")
    runtime: str = Field(default="ONNX Runtime", description="Runtime environment used")
    device: str = Field(default="Host CPU (Development Fallback)", description="Execution device verified")
    inference_time_ms: float | None = Field(default=None, description="Inference latency in milliseconds")
    file_id: str | None = Field(default=None, description="Analyzed file reference ID")
    timing: TimingMetrics | None = Field(default=None, description="Detailed stage latency breakdown")
    image: ImageMetadata | None = Field(default=None, description="Analyzed image dimensions")
    model: ModelInferenceMetadata | None = Field(default=None, description="Model metadata")
    verification: RuntimeVerificationMetadata | None = Field(default=None, description="Hardware verification status")


class FrameCaptureRequest(BaseModel):
    image_base64: str = Field(..., description="Captured camera frame in base64")


class FrameCaptureResponse(BaseModel):
    status: str = "CAPTURED"
    frame_id: str
    file_id: str
    file_path: str
    size_bytes: int
    attachment_id: int | None = None
    message: str = "Frame captured and stored locally."
