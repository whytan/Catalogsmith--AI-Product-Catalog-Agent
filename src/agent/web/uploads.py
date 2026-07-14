from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from agent.web.catalog_images import IMAGE_EXTENSIONS, PRODUCTS_DIR

MAX_IMAGE_BYTES = 5 * 1024 * 1024
CONTENT_TYPE_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _safe_stem(name: str) -> str:
    stem = Path(name).stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return stem[:40] or "product"


def _extension(file: UploadFile, header: bytes) -> str:
    if file.content_type in CONTENT_TYPE_TO_EXT:
        return CONTENT_TYPE_TO_EXT[file.content_type]
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return suffix
    if header.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return ".webp"
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return ".gif"
    raise HTTPException(status_code=400, detail="Unsupported image type. Use JPG, PNG, WebP, or GIF.")


async def save_product_image(file: UploadFile) -> tuple[str, str]:
    """Save an uploaded product image. Returns (filename, public_url)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")

    header = await file.read(16)
    if not header:
        raise HTTPException(status_code=400, detail="Empty file.")

    rest = await file.read()
    data = header + rest
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Image too large (max 5 MB).")

    ext = _extension(file, header)
    stem = _safe_stem(file.filename)
    filename = f"{stem}-{uuid.uuid4().hex[:10]}{ext}"

    PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = PRODUCTS_DIR / filename
    dest.write_bytes(data)

    return filename, f"/static/products/{filename}"
