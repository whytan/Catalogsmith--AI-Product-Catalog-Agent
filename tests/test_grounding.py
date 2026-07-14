from decimal import Decimal

import pytest

from agent.guardrails.grounding import check_grounding
from agent.pipeline.nodes.validate import ValidatedProduct


def _product(**overrides) -> ValidatedProduct:
    base = {
        "name": "Aurora Earbuds",
        "price": Decimal("2499.00"),
        "category": "electronics",
        "features": ["8-hour battery", "ANC"],
        "ingredients": [],
        "materials": [],
        "photo_filename": "",
    }
    base.update(overrides)
    return ValidatedProduct(**base)


def test_ground_check_flags_unsupported_waterproof() -> None:
    product = _product()
    description = "Reliable earbuds with ANC. Fully waterproof for all conditions."
    violations = check_grounding(description, product)
    assert any(item.claim == "waterproof" for item in violations)


def test_ground_check_allows_supported_waterproof_fact() -> None:
    product = _product(features=["8-hour battery", "ANC", "IPX7 waterproof"])
    description = "IPX7 waterproof protection for daily workouts."
    violations = check_grounding(description, product)
    assert not violations


def test_ground_check_flags_organic_without_fact() -> None:
    product = _product(category="beauty", features=["vitamin C"])
    description = "An organic serum for brighter skin."
    violations = check_grounding(description, product)
    assert any(item.claim == "organic" for item in violations)
