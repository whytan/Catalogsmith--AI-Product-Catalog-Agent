from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from agent.config import settings
from agent.db.schema import RunRow, utcnow


@dataclass
class LLMUsage:
    tokens_in: int
    tokens_out: int
    cost: Decimal
    latency_ms: int
    model: str


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> Decimal:
    deployment = model.lower()
    if settings.azure_openai_deployment_mini.lower() in deployment or "mini" in deployment:
        in_rate = settings.mini_input_cost_per_1m
        out_rate = settings.mini_output_cost_per_1m
    else:
        in_rate = settings.frontier_input_cost_per_1m
        out_rate = settings.frontier_output_cost_per_1m

    cost = (tokens_in / 1_000_000 * in_rate) + (tokens_out / 1_000_000 * out_rate)
    return Decimal(str(round(cost, 6)))


async def log_run(
    session: AsyncSession,
    *,
    node: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    latency_ms: int,
    product_id: int | None = None,
) -> RunRow:
    row = RunRow(
        product_id=product_id,
        node=node,
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost=estimate_cost(model, tokens_in, tokens_out),
        latency_ms=latency_ms,
        created_at=utcnow(),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def total_cost_for_product(session: AsyncSession, product_id: int) -> Decimal:
    from sqlalchemy import func, select

    result = await session.execute(
        select(func.coalesce(func.sum(RunRow.cost), 0)).where(RunRow.product_id == product_id)
    )
    value = result.scalar_one()
    return Decimal(str(value))
