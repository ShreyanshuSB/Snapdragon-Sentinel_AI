from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field
from app.schemas.vision import BoundingBox


class TextRegion(BaseModel):
    id: str = Field(..., description="Unique region identifier")
    text: str = Field(..., description="Recognized text string")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model recognition confidence score")
    bbox: BoundingBox = Field(..., description="Aligned bounding box coordinates")
    polygon: list[list[float]] | None = Field(default=None, description="Optional 4-point polygon coordinates")
    language: str | None = Field(default="en", description="Detected language/script")
    reading_order: int | None = Field(default=None, description="Deterministic spatial reading order index")


class OCRTimingMetrics(BaseModel):
    preprocess_ms: float = Field(..., description="Image normalization and formatting latency")
    detector_ms: float = Field(..., description="Text detection (CRAFT) pass latency in ms")
    recognizer_ms: float = Field(..., description="Text recognition (CRNN) pass latency in ms")
    postprocess_ms: float = Field(..., description="Box un-warping, sorting, and text formatting latency")
    total_ms: float = Field(..., description="Total pipeline latency in ms")


class OCRModelMetadata(BaseModel):
    name: str = "EasyOCR (Detector + Recognizer)"
    detector: str = "CRAFT (Character Region Awareness for Text Detection)"
    recognizer: str = "CRNN (Convolutional Recurrent Neural Network)"
    runtime: str = "ONNX Runtime / Local Torch"
    license: str = "Apache-2.0"
    languages: list[str] = Field(default_factory=lambda: ["en"])
    input_resolution: str = "Dynamic / Preserved Aspect Ratio"


class OCRAnalyzeRequest(BaseModel):
    file_id: str | None = Field(default=None, description="Attachment file reference ID")
    image: str | None = Field(default=None, description="Base64 encoded image string")
    languages: list[str] = Field(default_factory=lambda: ["en"], description="Requested OCR language models")
    confidence_threshold: float = Field(default=0.2, ge=0.01, le=1.0, description="Minimum confidence filter")


class OCRResult(BaseModel):
    status: str = Field(default="READY", description="Pipeline status code")
    message: str = Field(..., description="Execution status description")
    regions: list[TextRegion] = Field(default_factory=list, description="Extracted text regions with bounding boxes")
    full_text: str = Field(default="", description="Full reconstructed text organized in reading order")
    region_count: int = Field(default=0, description="Count of detected text regions")
    timing: OCRTimingMetrics | None = Field(default=None, description="Detailed stage latency metrics")
    model: OCRModelMetadata | None = Field(default=None, description="OCR model architecture metadata")
    execution_provider: str = Field(default="CPUExecutionProvider", description="Active execution provider")
    device: str = Field(default="Host CPU (Development Fallback)", description="Execution device")
    npu_verified: bool = Field(default=False, description="Whether NPU acceleration is verified")
    source: str = Field(default="image", description="Text origin source reference")


class OCRStatusResponse(BaseModel):
    state: str
    is_available: bool
    is_loaded: bool
    model_name: str
    detector: str
    recognizer: str
    runtime: str
    execution_provider: str
    npu_verified: bool
    supported_languages: list[str]
    device_label: str
