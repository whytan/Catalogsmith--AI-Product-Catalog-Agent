"""Frozen product fixtures for the learning ablation (unique names per run)."""

from __future__ import annotations

from decimal import Decimal

from agent.pipeline.nodes.validate import ValidatedProduct

# Diverse categories — same set used for both ON and OFF arms.
ABLATION_PRODUCTS: list[ValidatedProduct] = [
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
]
