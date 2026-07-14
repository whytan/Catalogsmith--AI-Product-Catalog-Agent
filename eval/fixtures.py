"""Frozen product fixtures for the learning ablation (unique names per run).

Order matters: first product in each category intentionally seeds rubric
violation-comments so later same-category products can learn from memory.
"""

from __future__ import annotations

from decimal import Decimal

from agent.pipeline.nodes.validate import ValidatedProduct

# N≈10 — 4 electronics / 3 kitchen / 3 beauty. Seeders first per category.
ABLATION_PRODUCTS: list[ValidatedProduct] = [
    # Category seeders (trip rubric on first probe pass)
    ValidatedProduct(
        name="Ablation Probe Earbuds A1",
        price=Decimal("1999.00"),
        category="electronics",
        features=["8-hour battery", "ANC", "USB-C charging"],
        materials=["ABS plastic"],
    ),
    ValidatedProduct(
        name="Ablation Probe Kettle K2",
        price=Decimal("2199.00"),
        category="kitchen",
        features=["1.0L capacity", "gooseneck spout", "built-in thermometer"],
        materials=["stainless steel"],
    ),
    ValidatedProduct(
        name="Ablation Probe Serum S3",
        price=Decimal("999.00"),
        category="beauty",
        features=["30ml bottle", "fragrance-free", "vitamin C"],
        ingredients=["hyaluronic acid", "niacinamide"],
        materials=["glass bottle"],
    ),
    # Second wave — ON arm should learn from seeders
    ValidatedProduct(
        name="Ablation Probe Speaker P4",
        price=Decimal("4599.00"),
        category="electronics",
        features=["12-hour battery", "Bluetooth 5.3", "IPX7 waterproof"],
        materials=["aluminium grille"],
    ),
    ValidatedProduct(
        name="Ablation Probe Board B5",
        price=Decimal("899.00"),
        category="kitchen",
        features=["18x12 inches", "juice groove", "antibacterial bamboo"],
        materials=["bamboo"],
    ),
    ValidatedProduct(
        name="Ablation Probe Mask M6",
        price=Decimal("749.00"),
        category="beauty",
        features=["75ml tube", "sensitive-skin safe", "weekly use"],
        ingredients=["kaolin clay", "aloe vera"],
        materials=["aluminium tube"],
    ),
    # Third wave — more same-category priors for memory
    ValidatedProduct(
        name="Ablation Probe Charger C7",
        price=Decimal("1299.00"),
        category="electronics",
        features=["65W GaN", "USB-C PD", "foldable pins"],
        materials=["polycarbonate"],
    ),
    ValidatedProduct(
        name="Ablation Probe Mug Set G8",
        price=Decimal("1599.00"),
        category="kitchen",
        features=["set of 2", "16oz each", "double-wall"],
        materials=["ceramic"],
    ),
    ValidatedProduct(
        name="Ablation Probe Scrub R9",
        price=Decimal("649.00"),
        category="beauty",
        features=["200g jar", "sugar exfoliant", "cruelty-free"],
        ingredients=["cane sugar", "sweet orange oil"],
        materials=["glass jar"],
    ),
    ValidatedProduct(
        name="Ablation Probe Band W10",
        price=Decimal("1899.00"),
        category="electronics",
        features=["heart-rate sensor", "7-day battery", "sleep tracking"],
        materials=["silicone strap"],
    ),
]
