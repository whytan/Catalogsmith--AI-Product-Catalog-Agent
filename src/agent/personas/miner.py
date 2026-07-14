from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.adapter.sqlite import SQLiteStorefrontAdapter
from agent.db.schema import SignalRow, dumps_json, loads_json
from agent.models.product import Product


@dataclass
class SignalCluster:
    product_id: int
    theme: str
    count: int
    sample_questions: list[str]
    persona_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "theme": self.theme,
            "count": self.count,
            "sample_questions": self.sample_questions,
            "persona_count": self.persona_count,
            "summary": f"{self.persona_count} persona signal(s) asked about {self.theme}",
        }


async def mine_signal_clusters(session: AsyncSession, *, product_id: int | None = None) -> list[SignalCluster]:
    stmt = select(SignalRow).where(SignalRow.kind == "question")
    if product_id is not None:
        stmt = stmt.where(SignalRow.product_id == product_id)
    result = await session.execute(stmt)
    rows = result.scalars().all()

    grouped: dict[tuple[int, str], list[SignalRow]] = defaultdict(list)
    for row in rows:
        payload = loads_json(row.payload)
        theme = payload.get("theme") or "general"
        grouped[(row.product_id, theme)].append(row)

    clusters: list[SignalCluster] = []
    for (pid, theme), items in grouped.items():
        if len(items) < 1:
            continue
        questions = [loads_json(item.payload).get("text", "") for item in items if item.payload]
        personas = {item.persona_id for item in items if item.persona_id is not None}
        clusters.append(
            SignalCluster(
                product_id=pid,
                theme=theme,
                count=len(items),
                sample_questions=[q for q in questions if q][:3],
                persona_count=len(personas) or len(items),
            )
        )

    clusters.sort(key=lambda cluster: (-cluster.count, cluster.product_id, cluster.theme))
    return clusters


async def propose_rewrite(session: AsyncSession, product_id: int, theme: str) -> dict[str, Any]:
    adapter = SQLiteStorefrontAdapter(session)
    product = await adapter.get_product(product_id)
    if product is None:
        raise ValueError(f"Product {product_id} not found.")

    proposed = _rewrite_description(product, theme)
    reason = f"SYNTHETIC cluster: shoppers asked about {theme} ({theme} theme mined from persona questions)."
    return {
        "synthetic": True,
        "product_id": product_id,
        "theme": theme,
        "reason": reason,
        "current_description": product.description,
        "proposed_description": proposed,
    }


def _rewrite_description(product: Product, theme: str) -> str:
    base = product.description.strip()
    if theme == "battery":
        feature = next((f for f in product.facts.features if "battery" in f.lower()), "long battery life")
        return f"{base} Highlights {feature} for buyers comparing runtime."
    if theme == "price":
        return f"{base} Strong value at Rs {product.price} for everyday use."
    if theme == "gift_suitability":
        return f"{base} A thoughtful gift option with clear quality cues for recipients."
    if theme == "specs":
        specs = ", ".join(product.facts.features[:3]) or "key product specs"
        materials = ", ".join(product.facts.materials[:2])
        extra = f" Materials: {materials}." if materials else ""
        return f"{base} Specs called out: {specs}.{extra}"
    return f"{base} Updated to address common shopper questions about {theme}."


async def question_frequency(session: AsyncSession, *, product_id: int, theme: str) -> int:
    result = await session.execute(
        select(SignalRow).where(
            SignalRow.product_id == product_id,
            SignalRow.kind == "question",
        )
    )
    count = 0
    for row in result.scalars().all():
        payload = loads_json(row.payload)
        if payload.get("theme") == theme:
            count += 1
    return count
