from __future__ import annotations

import base64
import io
import logging
import os
from PIL import Image
from sqlalchemy.orm import Session

from app.ai.ocr.ocr_engine import ocr_engine
from app.core.benchmark_manager import BenchmarkRecord
from app.database.models import Attachment
from app.schemas.ocr import OCRAnalyzeRequest, OCRResult, OCRStatusResponse

logger = logging.getLogger("sentinel.services.ocr_service")


class OCRService:
    """High-level application service orchestrating OCR operations."""

    def analyze_image(self, request: OCRAnalyzeRequest | None, db: Session) -> OCRResult:
        if not request or (not request.file_id and not request.image):
            raise ValueError("Either 'file_id' or 'image' base64 payload must be provided for OCR analysis.")

        pil_image: Image.Image | None = None

        if request.file_id:
            att = db.query(Attachment).filter(Attachment.file_id == request.file_id).first()
            if not att or not os.path.exists(att.file_path):
                raise FileNotFoundError(f"Attachment file '{request.file_id}' not found.")
            pil_image = Image.open(att.file_path)
        elif request.image:
            image_b64 = request.image
            if "," in image_b64:
                image_b64 = image_b64.split(",", 1)[1]
            try:
                img_bytes = base64.b64decode(image_b64)
                pil_image = Image.open(io.BytesIO(img_bytes))
            except Exception as e:
                raise ValueError(f"Invalid base64 image data: {e}") from e

        if pil_image is None:
            raise ValueError("Failed to decode image for OCR.")

        confidence_threshold = request.confidence_threshold if request else 0.2
        return ocr_engine.process_image(pil_image, confidence_threshold=confidence_threshold)

    def get_status(self) -> OCRStatusResponse:
        return ocr_engine.get_status()

    def run_benchmark(
        self,
        file_id: str | None = None,
        warmup: int = 2,
        runs: int = 5,
        db: Session | None = None,
    ) -> BenchmarkRecord:
        if file_id and db:
            att = db.query(Attachment).filter(Attachment.file_id == file_id).first()
            if not att or not os.path.exists(att.file_path):
                raise FileNotFoundError(f"Attachment file '{file_id}' not found.")
            img = Image.open(att.file_path)
        else:
            # Create standard test image
            from PIL import ImageDraw
            img = Image.new("RGB", (600, 200), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)
            draw.text((30, 40), "SENTINEL LOCAL OCR BENCHMARK 2026", fill=(0, 0, 0))
            draw.text((30, 90), "QUALCOMM SNAPDRAGON COPILOT+ AI", fill=(0, 0, 0))

        return ocr_engine.run_benchmark(img, warmup_runs=warmup, measured_runs=runs)


ocr_service = OCRService()
