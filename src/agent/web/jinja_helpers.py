"""Shared Jinja2 helpers for catalog templates."""

from __future__ import annotations

from typing import Any

from agent.web.catalog_images import product_image_url


def _photo_filename_from_obj(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, dict):
        facts = obj.get("facts")
        if isinstance(facts, dict):
            return str(facts.get("photo_filename") or "")
        if facts is not None:
            return str(getattr(facts, "photo_filename", "") or "")
        return str(obj.get("photo_filename") or "")
    facts = getattr(obj, "facts", None)
    if facts is not None:
        if isinstance(facts, dict):
            return str(facts.get("photo_filename") or "")
        return str(getattr(facts, "photo_filename", "") or "")
    return str(getattr(obj, "photo_filename", "") or "")


def jinja_product_image(obj: Any) -> str | None:
    return product_image_url(_photo_filename_from_obj(obj))


def register_template_globals(env) -> None:
    env.filters["product_image"] = jinja_product_image
