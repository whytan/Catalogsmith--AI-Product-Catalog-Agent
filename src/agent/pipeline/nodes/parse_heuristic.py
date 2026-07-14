from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from agent.categories import VALID_CATEGORIES
from agent.models.product import ProductFacts

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "electronics": ["earbuds", "earbud", "speaker", "lamp", "band", "bluetooth", "wireless", "usb", "iphone", "smartphone", "phone", "tablet", "android"],
    "kitchen": ["kettle", "board", "mug", "mortar", "pestle", "kitchen", "pour-over", "cutting"],
    "beauty": ["serum", "mask", "scrub", "beauty", "skin", "face", "clay"],
}

PRICE_PATTERN = re.compile(
    r"(?:₹|rs\.?|inr)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)|"
    r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*(?:₹|rs\.?|inr)",
    re.IGNORECASE,
)
BARE_PRICE_PATTERN = re.compile(
    r"(?<![xX/\d])([1-9]\d{2,4})(?![xX]\d|\s*(?:x|inch|inches|cm|ml|g)\b)",
)
PHOTO_PATTERN = re.compile(r"(?:photo|image|filename)\s*[:=]\s*([^\s,;]+)", re.IGNORECASE)
FEATURE_SPLIT = re.compile(r"[,;|\n]|(?:\s+—\s+)")
ACRONYM_PATTERN = re.compile(r"\b[A-Z]{2,6}\b")
SKIP_ACRONYMS = {"INR", "RS", "IP"}


def _parse_price(raw: str) -> Decimal | None:
    if re.search(r"-\s*(?:₹|rs\.?|inr)?\s*[0-9]", raw, re.IGNORECASE):
        return Decimal("-1")

    match = PRICE_PATTERN.search(raw)
    if match:
        value = (match.group(1) or match.group(2) or "").replace(",", "")
        try:
            return Decimal(value)
        except InvalidOperation:
            return None

    bare = BARE_PRICE_PATTERN.search(raw)
    if bare:
        try:
            return Decimal(bare.group(1))
        except InvalidOperation:
            return None
    return None


def _infer_category(raw: str) -> str:
    lowered = raw.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if re.search(rf"\b{category}\b", lowered):
            return category
        if any(re.search(rf"\b{re.escape(keyword)}\b", lowered) for keyword in keywords):
            return category
    return ""


def _strip_price_tokens(text: str) -> str:
    text = PRICE_PATTERN.sub("", text)
    text = BARE_PRICE_PATTERN.sub("", text)
    text = re.sub(r"\b(?:₹|rs\.?|inr)\b", "", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip(" ,-")


def _infer_name(raw: str) -> str:
    name_match = re.search(r"(?:name|product)\s*[:=]\s*([^,\n;]+)", raw, re.IGNORECASE)
    if name_match:
        return _trim_name(name_match.group(1).strip())[:200]

    first_segment = FEATURE_SPLIT.split(raw, maxsplit=1)[0].strip()
    cleaned = _strip_price_tokens(first_segment)
    return _trim_name(cleaned)[:200] if cleaned and len(cleaned) > 2 else ""


def _trim_name(name: str) -> str:
    for category in VALID_CATEGORIES:
        name = re.split(rf"\b{category}\b", name, maxsplit=1, flags=re.IGNORECASE)[0]
    return name.strip(" ,-")


def _feature_remainder(raw: str, name: str, category: str) -> str:
    remainder = raw
    if name:
        remainder = remainder.replace(name, "", 1)
    remainder = PRICE_PATTERN.sub("", remainder)
    remainder = BARE_PRICE_PATTERN.sub("", remainder)
    remainder = re.sub(r"\b(?:₹|rs\.?|inr)\b", "", remainder, flags=re.IGNORECASE)
    if category:
        remainder = re.sub(rf"\b{category}\b", "", remainder, flags=re.IGNORECASE)
    return remainder


def _split_list(value: str) -> list[str]:
    return [part.strip() for part in FEATURE_SPLIT.split(value) if part.strip()]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _is_noise_segment(part: str, name: str) -> bool:
    lowered = part.lower().strip()
    if not lowered:
        return True
    if lowered in VALID_CATEGORIES:
        return True
    if name and lowered == name.lower():
        return True
    if PRICE_PATTERN.search(part) or BARE_PRICE_PATTERN.fullmatch(part.strip()):
        return True
    if PHOTO_PATTERN.search(part):
        return True
    if re.fullmatch(r"(?:₹|rs\.?|inr)", lowered):
        return True
    return False


def _extract_features(raw: str, name: str, category: str) -> list[str]:
    features: list[str] = []

    feature_match = re.search(r"features?\s*[:=]\s*(.+)", raw, re.IGNORECASE)
    if feature_match:
        features.extend(_split_list(feature_match.group(1)))

    for part in _split_list(_feature_remainder(raw, name, category)):
        part = part.strip()
        if _is_noise_segment(part, name):
            continue
        if len(part) <= 80:
            features.append(part)

    for acronym in ACRONYM_PATTERN.findall(raw):
        if acronym not in SKIP_ACRONYMS:
            features.append(acronym)

    return _dedupe(features)[:12]


def parse_heuristic(raw: str) -> ProductFacts:
    """Offline / mock parser for development and golden-set tests."""
    normalized = raw.replace("—", ",")
    photo_match = PHOTO_PATTERN.search(normalized)
    photo_filename = photo_match.group(1).strip() if photo_match else ""

    ingredients: list[str] = []
    materials: list[str] = []
    ing_match = re.search(r"ingredients?\s*[:=]\s*(.+)", normalized, re.IGNORECASE)
    if ing_match:
        ingredients = _split_list(ing_match.group(1))
    mat_match = re.search(r"materials?\s*[:=]\s*(.+)", normalized, re.IGNORECASE)
    if mat_match:
        materials = _split_list(mat_match.group(1))

    name = _infer_name(normalized)
    category = _infer_category(normalized)
    return ProductFacts(
        name=name,
        price=_parse_price(normalized),
        category=category,
        features=_extract_features(normalized, name, category),
        ingredients=ingredients,
        materials=materials,
        photo_filename=photo_filename,
    )
