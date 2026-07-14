"""Seed data and idempotent seeding for the demo storefront."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.adapter.sqlite import SQLiteStorefrontAdapter
from agent.db.schema import ProductRow
from agent.models.product import ProductCreate, ProductFacts, ProductStatus

SEED_PRODUCTS: list[ProductCreate] = [
    ProductCreate(
        name="Aurora Wireless Earbuds",
        price=Decimal("2499.00"),
        category="electronics",
        description=(
            "True-wireless earbuds with 8-hour battery life, active noise cancellation, "
            "and a compact USB-C charging case."
        ),
        facts=ProductFacts(
            name="Aurora Wireless Earbuds",
            price=Decimal("2499.00"),
            category="electronics",
            features=["8-hour battery", "ANC", "IPX5 water resistance", "USB-C charging"],
            materials=["ABS plastic", "silicone ear tips"],
            photo_filename="aurora-earbuds.jpg",
        ),
        status=ProductStatus.PUBLISHED,
    ),
    ProductCreate(
        name="Pulse Fitness Band",
        price=Decimal("1899.00"),
        category="electronics",
        description=(
            "Lightweight fitness band with heart-rate tracking, sleep monitoring, "
            "and 7-day battery on a single charge."
        ),
        facts=ProductFacts(
            name="Pulse Fitness Band",
            price=Decimal("1899.00"),
            category="electronics",
            features=["heart-rate sensor", "sleep tracking", "7-day battery", "water resistant"],
            materials=["silicone strap", "polycarbonate body"],
            photo_filename="pulse-band.jpg",
        ),
        status=ProductStatus.PUBLISHED,
    ),
    ProductCreate(
        name="Lumen Desk Lamp",
        price=Decimal("3299.00"),
        category="electronics",
        description=(
            "Adjustable LED desk lamp with warm-to-cool color temperature and "
            "a touch dimmer for comfortable late-night reading."
        ),
        facts=ProductFacts(
            name="Lumen Desk Lamp",
            price=Decimal("3299.00"),
            category="electronics",
            features=["touch dimmer", "3000K–6000K", "USB-A charging port"],
            materials=["aluminum arm", "ABS base"],
            photo_filename="lumen-lamp.jpg",
        ),
        status=ProductStatus.PUBLISHED,
    ),
    ProductCreate(
        name="Nova Portable Speaker",
        price=Decimal("4599.00"),
        category="electronics",
        description=(
            "Palm-sized Bluetooth speaker with 12-hour playback and IPX7 waterproofing — "
            "ready for desk or trail."
        ),
        facts=ProductFacts(
            name="Nova Portable Speaker",
            price=Decimal("4599.00"),
            category="electronics",
            features=["12-hour battery", "Bluetooth 5.3", "IPX7 waterproof"],
            materials=["aluminum grille", "rubberized shell"],
            photo_filename="nova-speaker.jpg",
        ),
        status=ProductStatus.PUBLISHED,
    ),
    ProductCreate(
        name="Cedar Pour-Over Kettle",
        price=Decimal("2199.00"),
        category="kitchen",
        description=(
            "Gooseneck kettle with precise pour control and a built-in thermometer "
            "for consistent pour-over coffee."
        ),
        facts=ProductFacts(
            name="Cedar Pour-Over Kettle",
            price=Decimal("2199.00"),
            category="kitchen",
            features=["1.0L capacity", "built-in thermometer", "gooseneck spout"],
            materials=["stainless steel"],
            photo_filename="cedar-kettle.jpg",
        ),
        status=ProductStatus.PUBLISHED,
    ),
    ProductCreate(
        name="Bamboo Cutting Board",
        price=Decimal("899.00"),
        category="kitchen",
        description=(
            "Large bamboo board with a juice groove — gentle on knives and naturally "
            "resistant to bacteria."
        ),
        facts=ProductFacts(
            name="Bamboo Cutting Board",
            price=Decimal("899.00"),
            category="kitchen",
            features=["18x12 inches", "juice groove", "antibacterial bamboo"],
            materials=["bamboo"],
            photo_filename="bamboo-board.jpg",
        ),
        status=ProductStatus.PUBLISHED,
    ),
    ProductCreate(
        name="Stone Mortar & Pestle",
        price=Decimal("1299.00"),
        category="kitchen",
        description=(
            "Heavy granite mortar and pestle for grinding spices and pastes — "
            "the kind that lasts decades."
        ),
        facts=ProductFacts(
            name="Stone Mortar & Pestle",
            price=Decimal("1299.00"),
            category="kitchen",
            features=["14cm bowl", "non-slip base", "unpolished interior"],
            materials=["granite"],
            photo_filename="mortar-pestle.jpg",
        ),
        status=ProductStatus.PUBLISHED,
    ),
    ProductCreate(
        name="Copper Moscow Mule Mug Set",
        price=Decimal("1599.00"),
        category="kitchen",
        description=(
            "Set of two hammered copper mugs with lacquer lining — keeps cocktails "
            "cold and looks sharp on the shelf."
        ),
        facts=ProductFacts(
            name="Copper Moscow Mule Mug Set",
            price=Decimal("1599.00"),
            category="kitchen",
            features=["set of 2", "16oz each", "lacquer-lined"],
            materials=["copper", "stainless steel lining"],
            photo_filename="copper-mugs.jpg",
        ),
        status=ProductStatus.PUBLISHED,
    ),
    ProductCreate(
        name="Riverstone Face Serum",
        price=Decimal("999.00"),
        category="beauty",
        description=(
            "Daily hydrating serum with hyaluronic acid and vitamin C for brighter, "
            "smoother skin without fragrance."
        ),
        facts=ProductFacts(
            name="Riverstone Face Serum",
            price=Decimal("999.00"),
            category="beauty",
            features=["30ml bottle", "fragrance-free", "dermatologist tested"],
            ingredients=["hyaluronic acid", "vitamin C", "niacinamide", "glycerin"],
            materials=["glass bottle"],
            photo_filename="riverstone-serum.jpg",
        ),
        status=ProductStatus.PUBLISHED,
    ),
    ProductCreate(
        name="Meadow Clay Mask",
        price=Decimal("749.00"),
        category="beauty",
        description=(
            "Weekly kaolin clay mask that draws out impurities without stripping — "
            "suitable for sensitive skin."
        ),
        facts=ProductFacts(
            name="Meadow Clay Mask",
            price=Decimal("749.00"),
            category="beauty",
            features=["75ml tube", "sensitive-skin safe", "weekly use"],
            ingredients=["kaolin clay", "aloe vera", "chamomile extract"],
            materials=["aluminum tube"],
            photo_filename="meadow-mask.jpg",
        ),
        status=ProductStatus.PUBLISHED,
    ),
    ProductCreate(
        name="Silk Sleep Mask",
        price=Decimal("599.00"),
        category="beauty",
        description=(
            "Mulberry silk sleep mask with an adjustable strap — blocks light gently "
            "without pressing on your eyes."
        ),
        facts=ProductFacts(
            name="Silk Sleep Mask",
            price=Decimal("599.00"),
            category="beauty",
            features=["adjustable strap", "light-blocking", "machine washable bag"],
            materials=["mulberry silk"],
            photo_filename="silk-mask.jpg",
        ),
        status=ProductStatus.PUBLISHED,
    ),
    ProductCreate(
        name="Citrus Body Scrub",
        price=Decimal("649.00"),
        category="beauty",
        description=(
            "Sugar-based body scrub with sweet orange oil — exfoliates dry skin and "
            "leaves a fresh, subtle scent."
        ),
        facts=ProductFacts(
            name="Citrus Body Scrub",
            price=Decimal("649.00"),
            category="beauty",
            features=["200g jar", "sugar exfoliant", "cruelty-free"],
            ingredients=["cane sugar", "sweet orange oil", "coconut oil", "vitamin E"],
            materials=["glass jar"],
            photo_filename="citrus-scrub.jpg",
        ),
        status=ProductStatus.PUBLISHED,
    ),
]


async def seed_if_empty(session: AsyncSession) -> int:
    """Insert demo products when the catalog is empty. Idempotent."""
    count_result = await session.execute(select(func.count()).select_from(ProductRow))
    if count_result.scalar_one() > 0:
        return 0

    adapter = SQLiteStorefrontAdapter(session)
    for product in SEED_PRODUCTS:
        await adapter.create_product(product)
    return len(SEED_PRODUCTS)
