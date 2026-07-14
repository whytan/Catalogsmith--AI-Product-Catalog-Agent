from __future__ import annotations

import re

from agent.models.product import ProductFacts
from agent.pipeline.nodes.parse_heuristic import _infer_category, _parse_price


def enrich_facts_from_raw(facts: ProductFacts, raw_text: str) -> ProductFacts:
    """Fill gaps the LLM missed from structured spec sheets (Flipkart-style)."""
    updates: dict[str, object] = {}
    lowered = raw_text.lower()

    if not facts.name.strip():
        model_match = re.search(
            r"model name\s+([^|\n]+?)(?:\s*\||\s+(?:operating system|brand|color|in the box)\b)",
            raw_text,
            re.IGNORECASE,
        )
        if model_match:
            updates["name"] = model_match.group(1).strip()[:200]

    if not facts.category.strip():
        category = _infer_category(raw_text)
        if not category and any(
            token in lowered
            for token in ("smartphone", "iphone", "android", "mobile phone", "tablet", "phablet")
        ):
            category = "electronics"
        if category:
            updates["category"] = category

    if facts.price is None and re.search(
        r"(?:₹|rs\.?|inr|price|mrp)\s*[:=]?", raw_text, re.IGNORECASE
    ):
        price = _parse_price(raw_text)
        if price is not None and price > 0:
            updates["price"] = price

    if not facts.features and len(raw_text) > 200:
        highlights: list[str] = []
        spec_fields = (
            ("Operating System", r"operating system\s+([^\n|]+)"),
            ("Storage", r"internal storage\s+([^\n|]+)"),
            ("Primary Camera", r"primary camera\s+([^\n|]+)"),
            ("Battery", r"battery capacity\s+([^\n|]+)"),
            ("Display", r"display size\s+([^\n|]+)"),
        )
        for label, pattern in spec_fields:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                highlights.append(f"{label}: {match.group(1).strip()}")
        if highlights:
            updates["features"] = highlights[:8]

    if not updates:
        return facts

    merged = {**facts.model_dump(mode="json"), **updates}
    return ProductFacts.model_validate(merged)
