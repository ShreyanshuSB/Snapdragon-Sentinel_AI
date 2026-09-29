from __future__ import annotations

import io
import logging
import os
import time
from pathlib import Path
from typing import Any
from PIL import Image

from app.ai.ocr.ocr_engine import ocr_engine
from app.schemas.document import DocumentPageResponse, DocumentResponse
from app.schemas.ocr import TextRegion

logger = logging.getLogger("sentinel.services.document_parser")

MAX_DOCUMENT_PAGES = 50
SCANNED_PAGE_CHAR_THRESHOLD = 30


class DocumentParseResult:
    def __init__(
        self,
        source_type: str,
        status: str,
        page_count: int,
        ocr_pages_count: int,
        extracted_text: str,
        extraction_method: str,
        processing_time_ms: float,
        pages: list[dict[str, Any]],
        metadata: dict[str, Any],
        error_message: str | None = None,
    ) -> None:
        self.source_type = source_type
        self.status = status
        self.page_count = page_count
        self.ocr_pages_count = ocr_pages_count
        self.extracted_text = extracted_text
        self.extraction_method = extraction_method
        self.processing_time_ms = processing_time_ms
        self.pages = pages
        self.metadata = metadata
        self.error_message = error_message


class DocumentParser:
    """
    Robust local document parser handling text files, text-native PDFs,
    scanned/image PDFs, and image documents.
    """

    def parse_file(
        self,
        file_path: str,
        mime_type: str | None = None,
        force_ocr: bool = False,
    ) -> DocumentParseResult:
        start_time = time.perf_counter()
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Document file not found: {p.resolve()}")

        suffix = p.suffix.lower()

        # 1. Plain Text Documents
        if suffix in (".txt", ".md", ".json", ".csv", ".log") or (mime_type and "text/" in mime_type):
            return self._parse_text_file(p, start_time)

        # 2. PDF Documents (Hybrid native text vs. Scanned OCR)
        elif suffix == ".pdf" or (mime_type and "pdf" in mime_type):
            return self._parse_pdf_file(p, start_time, force_ocr=force_ocr)

        # 3. Image Documents (Single page OCR)
        elif suffix in (".png", ".jpg", ".jpeg", ".webp", ".bmp") or (mime_type and "image/" in mime_type):
            return self._parse_image_file(p, start_time)

        else:
            raise ValueError(f"Unsupported document format '{suffix}'. Supported: PDF, TXT, MD, CSV, PNG, JPG, WEBP.")

    def _parse_text_file(self, path: Path, start_time: float) -> DocumentParseResult:
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="latin-1")

        lines = content.splitlines()
        page_size = 60
        pages: list[dict[str, Any]] = []

        if not lines:
            page_chunks = [""]
        else:
            page_chunks = [
                "\n".join(lines[i : i + page_size]) for i in range(0, len(lines), page_size)
            ]

        for idx, chunk in enumerate(page_chunks, 1):
            pages.append({
                "page_number": idx,
                "width": 800.0,
                "height": 1100.0,
                "text": chunk,
                "has_ocr": False,
                "regions": [],
                "processing_time_ms": 1.0,
            })

        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        return DocumentParseResult(
            source_type="text_file",
            status="READY",
            page_count=len(pages),
            ocr_pages_count=0,
            extracted_text=content,
            extraction_method="direct_text_extraction",
            processing_time_ms=elapsed_ms,
            pages=pages,
            metadata={"line_count": len(lines), "encoding": "utf-8"},
        )

    def _parse_pdf_file(self, path: Path, start_time: float, force_ocr: bool = False) -> DocumentParseResult:
        from pypdf import PdfReader

        try:
            reader = PdfReader(str(path))
        except Exception as e:
            logger.exception("Failed to read PDF structure: %s", e)
            return DocumentParseResult(
                source_type="pdf",
                status="FAILED",
                page_count=0,
                ocr_pages_count=0,
                extracted_text="",
                extraction_method="pdf_reader_failed",
                processing_time_ms=round((time.perf_counter() - start_time) * 1000.0, 2),
                pages=[],
                metadata={"error": str(e)},
                error_message=f"Corrupt or invalid PDF file: {e}",
            )

        total_pages = min(len(reader.pages), MAX_DOCUMENT_PAGES)
        pages_data: list[dict[str, Any]] = []
        ocr_pages_count = 0
        all_text_blocks: list[str] = []

        # Check pypdfium2 availability for rendering scanned pages
        pdfium_doc = None
        try:
            import pypdfium2 as pdfium
            pdfium_doc = pdfium.PdfDocument(str(path))
        except Exception as e:
            logger.warning("pypdfium2 not available for page rendering: %s", e)

        for page_idx in range(total_pages):
            page_start = time.perf_counter()
            page_num = page_idx + 1
            page_obj = reader.pages[page_idx]
            page_w = float(page_obj.mediabox.width) if page_obj.mediabox else 612.0
            page_h = float(page_obj.mediabox.height) if page_obj.mediabox else 792.0

            extracted = ""
            try:
                extracted = page_obj.extract_text() or ""
            except Exception as e:
                logger.warning("pypdf extract_text failed on page %d: %s", page_num, e)

            # Check if page is text-native or scanned
            is_scanned = force_ocr or (len(extracted.strip()) < SCANNED_PAGE_CHAR_THRESHOLD)

            if is_scanned and pdfium_doc is not None:
                # Render page to image and run OCR
                try:
                    p_render = pdfium_doc[page_idx]
                    bitmap = p_render.render(scale=1.5)  # ~108 DPI for clean OCR without memory bloat
                    pil_img = bitmap.to_pil()
                    ocr_res = ocr_engine.process_image(pil_img)
                    page_text = ocr_res.full_text
                    regions = [r.model_dump() for r in ocr_res.regions]
                    has_ocr = True
                    ocr_pages_count += 1
                except Exception as e:
                    logger.exception("OCR rendering failed on page %d: %s", page_num, e)
                    page_text = extracted.strip()
                    regions = []
                    has_ocr = False
            else:
                # Pure native text extraction
                page_text = extracted.strip()
                regions = []
                has_ocr = False

            page_elapsed = round((time.perf_counter() - page_start) * 1000.0, 2)
            pages_data.append({
                "page_number": page_num,
                "width": page_w,
                "height": page_h,
                "text": page_text,
                "has_ocr": has_ocr,
                "regions": regions,
                "processing_time_ms": page_elapsed,
            })
            if page_text:
                all_text_blocks.append(page_text)

        full_doc_text = "\n\n".join(all_text_blocks)

        if ocr_pages_count == 0:
            source_type = "pdf_text"
            method = "native_pdf_text_extraction"
        elif ocr_pages_count == total_pages:
            source_type = "pdf_scanned"
            method = "scanned_pdf_easyocr"
        else:
            source_type = "pdf_mixed"
            method = "hybrid_pdf_text_and_ocr"

        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        return DocumentParseResult(
            source_type=source_type,
            status="READY" if full_doc_text or total_pages > 0 else "PARTIAL",
            page_count=total_pages,
            ocr_pages_count=ocr_pages_count,
            extracted_text=full_doc_text,
            extraction_method=method,
            processing_time_ms=elapsed_ms,
            pages=pages_data,
            metadata={
                "pdf_version": reader.pdf_header,
                "encrypted": reader.is_encrypted,
                "total_pages_in_file": len(reader.pages),
            },
        )

    def _parse_image_file(self, path: Path, start_time: float) -> DocumentParseResult:
        with Image.open(path) as img:
            w, h = img.size
            ocr_res = ocr_engine.process_image(img)

        regions = [r.model_dump() for r in ocr_res.regions]
        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        pages = [{
            "page_number": 1,
            "width": float(w),
            "height": float(h),
            "text": ocr_res.full_text,
            "has_ocr": True,
            "regions": regions,
            "processing_time_ms": elapsed_ms,
        }]

        return DocumentParseResult(
            source_type="image",
            status="READY",
            page_count=1,
            ocr_pages_count=1,
            extracted_text=ocr_res.full_text,
            extraction_method="image_easyocr",
            processing_time_ms=elapsed_ms,
            pages=pages,
            metadata={"width": w, "height": h, "regions_count": len(regions)},
        )


# Global document parser instance
document_parser = DocumentParser()
