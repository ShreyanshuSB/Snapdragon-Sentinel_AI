from __future__ import annotations

import hashlib
import os
import re
import uuid
from pathlib import Path
from typing import Tuple

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

# Allowed extensions and their expected MIME types & magic signatures
ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_DOC_EXTS = {".pdf", ".txt"}
ALLOWED_EXTS = ALLOWED_IMAGE_EXTS | ALLOWED_DOC_EXTS

MIME_EXT_MAP = {
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/webp": {".webp"},
    "application/pdf": {".pdf"},
    "text/plain": {".txt"},
}

MAGIC_SIGNATURES = {
    "png": b"\x89PNG\r\n\x1a\n",
    "jpeg": b"\xff\xd8\xff",
    "pdf": b"%PDF-",
}


def sanitize_filename(filename: str | None) -> str:
    if not filename:
        return "unnamed_file.bin"
    # Take basename only, strip path separators
    name = Path(filename).name
    # Keep alphanumeric, underscores, hyphens, and dots
    clean = re.sub(r"[^\w\s.-]", "", name).strip()
    return clean or "unnamed_file.bin"


def verify_file_signature(header: bytes, ext: str, mime: str) -> bool:
    """Verifies that the initial bytes match the expected signature for the extension and MIME."""
    if ext == ".png":
        return header.startswith(MAGIC_SIGNATURES["png"])
    if ext in (".jpg", ".jpeg"):
        return header.startswith(MAGIC_SIGNATURES["jpeg"])
    if ext == ".webp":
        return len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    if ext == ".pdf":
        return header.startswith(MAGIC_SIGNATURES["pdf"])
    if ext == ".txt":
        # Pure text shouldn't contain null bytes in initial 512 bytes
        if b"\x00" in header:
            return False
        try:
            header.decode("utf-8")
            return True
        except UnicodeDecodeError:
            try:
                header.decode("latin-1")
                return True
            except UnicodeDecodeError:
                return False
    return False


async def process_and_save_upload(
    file: UploadFile,
    target_dir: str | Path | None = None,
) -> Tuple[str, str, str, int, str, str]:
    """
    Validates extension, declared MIME, magic bytes, and max size via chunked streaming.
    Saves to safe isolated path and computes SHA-256.

    Returns:
        (file_id, safe_filename, target_path, file_size, content_type, sha256_hex)
    """
    original_name = sanitize_filename(file.filename)
    ext = Path(original_name).suffix.lower()

    if ext not in ALLOWED_EXTS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTS))}",
        )

    content_type = file.content_type or ""
    # Normalize image/jpg -> image/jpeg
    if content_type == "image/jpg":
        content_type = "image/jpeg"

    # Verify declared MIME matches extension
    valid_exts_for_mime = MIME_EXT_MAP.get(content_type)
    if valid_exts_for_mime is None or ext not in valid_exts_for_mime:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Declared MIME type '{content_type}' does not match extension '{ext}'.",
        )

    # Read first 512 bytes to check magic signature
    header = await file.read(512)
    if not header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if not verify_file_signature(header, ext, content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File signature does not match expected format for {ext}.",
        )

    save_dir = Path(target_dir or settings.upload_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    file_id = f"att_{uuid.uuid4().hex[:16]}"
    stored_name = f"{file_id}{ext}"
    target_path = save_dir / stored_name

    hasher = hashlib.sha256()
    hasher.update(header)
    total_size = len(header)

    try:
        with open(target_path, "wb") as dest:
            dest.write(header)
            while True:
                chunk = await file.read(64 * 1024)  # 64 KB chunks
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > settings.max_upload_size_bytes:
                    dest.close()
                    if target_path.exists():
                        target_path.unlink()
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum allowed size ({settings.max_upload_size_bytes // (1024 * 1024)} MB).",
                    )
                hasher.update(chunk)
                dest.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        )

    return (
        file_id,
        original_name,
        str(target_path.resolve()),
        total_size,
        content_type,
        hasher.hexdigest(),
    )
