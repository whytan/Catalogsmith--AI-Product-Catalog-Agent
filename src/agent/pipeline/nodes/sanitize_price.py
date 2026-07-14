from __future__ import annotations

import re
from decimal import Decimal

from agent.models.product import ProductFacts

# Selling-price labels — word-bounded; "cost" omitted (substring false positives).
EXPLICIT_PRICE_LABEL = re.compile(
    r"(?:₹|rs\.?|inr|\bprice\b|\bmrp\b|selling price|list price)\s*[:=]?\s*[\d,]+",
    re.IGNORECASE,
)


def _price_token(price: Decimal) -> str:
    return str(int(price)) if price == price.to_integral_value() else str(price)


def _price_value_in_text(price: Decimal, raw_text: str) -> bool:
    return _price_token(price) in raw_text.replace(",", "")


def is_spec_sheet_number(price_token: str, raw_text: str) -> bool:
    """True when this number is clearly a spec measurement, not a selling price."""
    escaped = re.escape(price_token)
    spec_patterns = (
        rf"\b{escaped}\s*mah\b",
        rf"\b{escaped}\s*(?:gb|mb|tb)\b",
        rf"\b{escaped}\s*(?:mhz|ghz|hz|ppi|mp|mm|cm|inch|fps|w)\b",
        rf"(?:battery|capacity)\s*[^0-9]{{0,40}}{escaped}\b",
        rf"\b{escaped}\s*(?:mah|gb|mb|mhz|ghz|ppi|mp)\b",
    )
    return any(re.search(pattern, raw_text, re.IGNORECASE) for pattern in spec_patterns)


def price_is_explicit_in_source(price: Decimal, raw_text: str) -> bool:
    """True only when this exact value appears next to a selling-price label."""
    if not _price_value_in_text(price, raw_text):
        return False

    token = re.escape(_price_token(price))
    labeled_patterns = (
        rf"(?:₹|rs\.?|inr)\s*{token}(?:\D|$)",
        rf"{token}\s*(?:₹|rs\.?|inr)\b",
        rf"(?:\bprice|\bmrp\b|selling price|list price)\s*[:=]?\s*{token}\b",
    )
    return any(re.search(pattern, raw_text, re.IGNORECASE) for pattern in labeled_patterns)


def sanitize_parsed_price(facts: ProductFacts, raw_text: str) -> ProductFacts:
    """Drop spec-sheet numbers (e.g. 3988 mAh) mistaken for product price."""
    if facts.price is None:
        return facts

    price = facts.price
    token = _price_token(price)

    # Spec contexts win — even if another labeled price exists elsewhere in the paste.
    if is_spec_sheet_number(token, raw_text):
        return facts.model_copy(update={"price": None})

    if price_is_explicit_in_source(price, raw_text):
        return facts

    if len(raw_text) > 200 and not EXPLICIT_PRICE_LABEL.search(raw_text):
        return facts.model_copy(update={"price": None})

    return facts.model_copy(update={"price": None})
