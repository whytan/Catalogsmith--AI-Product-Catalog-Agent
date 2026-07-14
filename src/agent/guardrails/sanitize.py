from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent.config import settings
from agent.models.product import ProductFacts

INJECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions?", re.IGNORECASE), ""),
    (re.compile(r"\band\s+write\s+ads\s+for\s+[^,;\n]+", re.IGNORECASE), ""),
    (re.compile(r"\bwrite\s+ads\s+for\s+[^,;\n]+", re.IGNORECASE), ""),
    (re.compile(r"\bSYSTEM\s*:\s*[^\n,;]+", re.IGNORECASE), ""),
    (re.compile(r"<\s*script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL), ""),
    (re.compile(r"<\s*script\b[^>]*>", re.IGNORECASE), ""),
    (re.compile(r"https?://\S+", re.IGNORECASE), ""),
    (re.compile(r"\bassistant\s*:\s*", re.IGNORECASE), ""),
    (re.compile(r"\buser\s*:\s*", re.IGNORECASE), ""),
]

INJECTION_MARKERS = (
    "ignore previous",
    "ignore all previous",
    "system:",
    "<script",
    "assistant:",
    "user:",
    "http://",
    "https://",
)


@dataclass
class SanitizeResult:
    text: str
    stripped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _apply_patterns(text: str) -> SanitizeResult:
    stripped: list[str] = []
    result = text
    for pattern, replacement in INJECTION_PATTERNS:
        while True:
            match = pattern.search(result)
            if not match:
                break
            stripped.append(match.group(0))
            result = pattern.sub(replacement, result, count=1)
    cleaned = re.sub(r"\s+", " ", result).strip(" ,;")
    warnings = [f"Removed untrusted content: {snippet[:120]}" for snippet in stripped]
    return SanitizeResult(text=cleaned, stripped=stripped, warnings=warnings)


def sanitize_text(text: str) -> SanitizeResult:
    """Strip instruction-like and unsafe content from untrusted seller input."""
    if settings.sanitizer_weak:
        return SanitizeResult(text=text)
    if not text.strip():
        return SanitizeResult(text=text)
    return _apply_patterns(text)


def sanitize_product_facts(facts: ProductFacts) -> tuple[ProductFacts, SanitizeResult]:
    """Sanitize every string field on parsed facts."""
    if settings.sanitizer_weak:
        return facts, SanitizeResult(text="")

    combined = SanitizeResult(text="")
    name_result = sanitize_text(facts.name)
    category_result = sanitize_text(facts.category)
    photo_result = sanitize_text(facts.photo_filename)

    features: list[str] = []
    for item in facts.features:
        cleaned = sanitize_text(item)
        combined.stripped.extend(cleaned.stripped)
        combined.warnings.extend(cleaned.warnings)
        if cleaned.text:
            features.append(cleaned.text)

    ingredients: list[str] = []
    for item in facts.ingredients:
        cleaned = sanitize_text(item)
        combined.stripped.extend(cleaned.stripped)
        combined.warnings.extend(cleaned.warnings)
        if cleaned.text:
            ingredients.append(cleaned.text)

    materials: list[str] = []
    for item in facts.materials:
        cleaned = sanitize_text(item)
        combined.stripped.extend(cleaned.stripped)
        combined.warnings.extend(cleaned.warnings)
        if cleaned.text:
            materials.append(cleaned.text)

    combined.stripped.extend(name_result.stripped + category_result.stripped + photo_result.stripped)
    combined.warnings.extend(name_result.warnings + category_result.warnings + photo_result.warnings)

    sanitized = ProductFacts(
        name=name_result.text,
        price=facts.price,
        category=category_result.text,
        features=features,
        ingredients=ingredients,
        materials=materials,
        photo_filename=photo_result.text,
    )
    return sanitized, combined


def contains_injection_markers(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in INJECTION_MARKERS)
