from __future__ import annotations

import json
import random
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.adapter.sqlite import SQLiteStorefrontAdapter
from agent.db.schema import PersonaRow, SignalRow, dumps_json, utcnow
from agent.models.product import Product, ProductStatus
from agent.personas.profiles import PersonaProfile, load_persona_profiles


def _pick_question(profile: PersonaProfile, product: Product) -> str:
    template = random.choice(profile.question_templates)
    return template.format(price=product.price)


def _review_text(profile: PersonaProfile, product: Product) -> str:
    if profile.persona_id == "bargain_hunter":
        return f"SYNTHETIC review: Feels pricey at Rs {product.price} for what is described."
    if profile.persona_id == "spec_reader":
        missing = "battery life" if "battery" not in product.description.lower() else "dimensions"
        return f"SYNTHETIC review: Listing is okay but does not mention {missing} clearly."
    if profile.persona_id == "skeptical_gifter":
        return "SYNTHETIC review: Not sure I would gift this without more reassurance on quality."
    return f"SYNTHETIC review: Quick take — {product.name} looks fine for casual buyers."


async def seed_personas(session: AsyncSession) -> int:
    existing = await session.execute(select(PersonaRow))
    if existing.scalars().first() is not None:
        return 0

    for profile in load_persona_profiles():
        session.add(
            PersonaRow(
                name=profile.name,
                profile_json=dumps_json(
                    {
                        "persona_id": profile.persona_id,
                        "focus": profile.focus,
                        "review_tone": profile.review_tone,
                        "cart_threshold": profile.cart_threshold,
                    }
                ),
            )
        )
    await session.commit()
    return len(load_persona_profiles())


async def _persona_map(session: AsyncSession) -> dict[str, PersonaRow]:
    result = await session.execute(select(PersonaRow))
    rows = result.scalars().all()
    mapping: dict[str, PersonaRow] = {}
    for row in rows:
        profile = json.loads(row.profile_json or "{}")
        mapping[profile.get("persona_id", row.name)] = row
    return mapping


async def run_persona_panel(
    session: AsyncSession,
    *,
    limit: int = 5,
    product_ids: list[int] | None = None,
    seed: int | None = 42,
) -> dict[str, Any]:
    """SYNTHETIC customer panel — browse published listings and emit signals."""
    if seed is not None:
        random.seed(seed)

    await seed_personas(session)
    adapter = SQLiteStorefrontAdapter(session)
    products = await adapter.list_products(status=ProductStatus.PUBLISHED.value)
    if product_ids:
        products = [product for product in products if product.id in product_ids]
    products = products[:limit]

    persona_rows = await _persona_map(session)
    profiles = load_persona_profiles()
    signals_created = 0

    for product in products:
        for profile in profiles:
            persona = persona_rows.get(profile.persona_id)
            if persona is None:
                continue

            session.add(
                SignalRow(
                    product_id=product.id,
                    persona_id=persona.id,
                    kind="view",
                    payload=dumps_json({"synthetic": True, "note": "Browsed listing"}),
                    created_at=utcnow(),
                )
            )
            signals_created += 1

            question = _pick_question(profile, product)
            session.add(
                SignalRow(
                    product_id=product.id,
                    persona_id=persona.id,
                    kind="question",
                    payload=dumps_json(
                        {
                            "synthetic": True,
                            "text": question,
                            "theme": _theme_from_question(question),
                        }
                    ),
                    created_at=utcnow(),
                )
            )
            signals_created += 1

            session.add(
                SignalRow(
                    product_id=product.id,
                    persona_id=persona.id,
                    kind="review",
                    payload=dumps_json({"synthetic": True, "text": _review_text(profile, product)}),
                    created_at=utcnow(),
                )
            )
            signals_created += 1

            if product.price <= profile.cart_threshold:
                session.add(
                    SignalRow(
                        product_id=product.id,
                        persona_id=persona.id,
                        kind="cart",
                        payload=dumps_json({"synthetic": True, "action": "add_to_cart"}),
                        created_at=utcnow(),
                    )
                )
                signals_created += 1

    await session.commit()
    return {
        "synthetic": True,
        "products": len(products),
        "personas": len(profiles),
        "signals_created": signals_created,
    }


def _theme_from_question(question: str) -> str:
    lowered = question.lower()
    if "battery" in lowered:
        return "battery"
    if "price" in lowered or "discount" in lowered or "worth" in lowered:
        return "price"
    if "gift" in lowered:
        return "gift_suitability"
    if "material" in lowered or "dimension" in lowered or "charging" in lowered:
        return "specs"
    return "general"
