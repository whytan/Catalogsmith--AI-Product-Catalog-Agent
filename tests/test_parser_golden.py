from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from agent.guardrails.sanitize import contains_injection_markers, sanitize_product_facts, sanitize_text
from agent.pipeline.nodes.parse_heuristic import parse_heuristic
from agent.pipeline.nodes.validate import validate_facts_structural

GOLDEN_ROOT = Path(__file__).resolve().parents[1] / "eval" / "golden"


def _load_cases() -> list[tuple[str, str, dict]]:
    cases: list[tuple[str, str, dict]] = []
    for case_dir in sorted(GOLDEN_ROOT.iterdir()):
        if not case_dir.is_dir():
            continue
        input_path = case_dir / "input.txt"
        expected_path = case_dir / "expected.json"
        cases.append(
            (
                case_dir.name,
                input_path.read_text(encoding="utf-8"),
                json.loads(expected_path.read_text(encoding="utf-8")),
            )
        )
    return cases


def _assert_contains(haystack: list[str], needles: list[str], *, extra: str = "") -> None:
    joined = " ".join(haystack + ([extra] if extra else [])).lower()
    for needle in needles:
        assert needle.lower() in joined, f"Expected feature '{needle}' in {haystack}"


def _assert_must_not_contain(facts_blob: str, patterns: list[str]) -> None:
    lowered = facts_blob.lower()
    for pattern in patterns:
        assert pattern.lower() not in lowered, f"Unexpected hostile content '{pattern}' in facts"


def _match_expected(facts, expected: dict) -> None:
    if expected.get("should_fail_validation"):
        result = validate_facts_structural(facts)
        assert not result.ok
        return

    if "name" in expected:
        assert facts.name == expected["name"]
    if "price" in expected:
        assert facts.price == Decimal(expected["price"])
    if "category" in expected:
        assert facts.category == expected["category"]
    if "photo_filename" in expected:
        assert facts.photo_filename == expected["photo_filename"]
    if "features_contains" in expected:
        _assert_contains(facts.features, expected["features_contains"], extra=facts.name)
    if "ingredients_contains" in expected:
        _assert_contains(facts.ingredients, expected["ingredients_contains"])
    if "materials_contains" in expected:
        _assert_contains(facts.materials, expected["materials_contains"])


@pytest.mark.parametrize("case_id,raw,expected", _load_cases(), ids=[c[0] for c in _load_cases()])
def test_parser_golden_set(case_id: str, raw: str, expected: dict) -> None:
    sanitized = sanitize_text(raw)
    facts = parse_heuristic(sanitized.text)
    facts, _meta = sanitize_product_facts(facts)

    if expected.get("must_not_contain"):
        blob = json.dumps(facts.model_dump(mode="json"))
        _assert_must_not_contain(blob, expected["must_not_contain"])

    _match_expected(facts, expected)


def test_golden_set_has_thirty_cases() -> None:
    assert len(_load_cases()) == 30
