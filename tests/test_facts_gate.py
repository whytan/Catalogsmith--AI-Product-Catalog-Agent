from decimal import Decimal

from agent.models.product import ProductFacts
from agent.pipeline.nodes.enrich_facts import enrich_facts_from_raw
from agent.pipeline.nodes.sanitize_price import sanitize_parsed_price
from agent.pipeline.nodes.validate import apply_facts_completion, validate_facts_structural


def test_strips_battery_mah_as_price() -> None:
    raw = "Model Name iPhone 17 Pro | Battery Capacity 3988 mAh | Smartphone Yes"
    facts = ProductFacts(name="iPhone 17 Pro", price=3988, category="electronics")
    cleaned = sanitize_parsed_price(facts, raw)
    assert cleaned.price is None


def test_strips_3988_even_when_other_price_label_in_paste() -> None:
    raw = (
        "Model Name iPhone 17 Pro | Battery Capacity 3988 mAh | "
        "Price: Rs 134900 | Smartphone Yes"
    )
    facts = ProductFacts(name="iPhone 17 Pro", price=3988, category="electronics")
    cleaned = sanitize_parsed_price(facts, raw)
    assert cleaned.price is None


def test_keeps_labeled_price_when_battery_also_in_paste() -> None:
    raw = "iPhone 17 Pro, Rs 134900, electronics, Battery Capacity 3988 mAh"
    facts = ProductFacts(name="iPhone 17 Pro", price=134900, category="electronics")
    cleaned = sanitize_parsed_price(facts, raw)
    assert cleaned.price == 134900


def test_keeps_explicit_rs_price() -> None:
    raw = "iPhone 17 Pro, Rs 134900, electronics, 256GB"
    facts = ProductFacts(name="iPhone 17 Pro", price=134900, category="electronics")
    cleaned = sanitize_parsed_price(facts, raw)
    assert cleaned.price == 134900


def test_enrich_spec_sheet_without_price() -> None:
    raw = (
        "Model Name iPhone 17 Pro | Operating System iOS 26 | "
        "Internal Storage 256 GB | Smartphone Yes"
    )
    facts = ProductFacts(name="", price=None, category="")
    enriched = enrich_facts_from_raw(facts, raw)
    assert enriched.name == "iPhone 17 Pro"
    assert enriched.category == "electronics"
    assert enriched.price is None


def test_apply_facts_completion_adds_price() -> None:
    facts = ProductFacts(name="iPhone 17 Pro", category="electronics", price=None)
    merged = apply_facts_completion(facts, {"price": "134900"})
    result = validate_facts_structural(merged)
    assert result.ok
    assert result.product is not None
    assert result.product.price == Decimal("134900")
