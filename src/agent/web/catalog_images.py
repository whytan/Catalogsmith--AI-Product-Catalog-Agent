"""Resolve catalog product image URLs from photo_filename."""

from __future__ import annotations

from pathlib import Path

PRODUCTS_DIR = Path(__file__).resolve().parent / "static" / "products"
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg")


def product_image_url(photo_filename: str | None) -> str | None:
    """Return a public static URL if a matching product image file exists."""
    if not photo_filename or not photo_filename.strip():
        return None

    name = Path(photo_filename.strip()).name
    stem = Path(name).stem

    candidates = [PRODUCTS_DIR / f"{stem}{ext}" for ext in IMAGE_EXTENSIONS]
    candidates.append(PRODUCTS_DIR / name)

    for path in candidates:
        if path.is_file():
            return f"/static/products/{path.name}"
    return None
