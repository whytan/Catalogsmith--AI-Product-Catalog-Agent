from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import update

from sqlalchemy.ext.asyncio import AsyncSession

from agent.llm.azure import AzureLLMClient
from agent.llm.cost import total_cost_for_product
from agent.db.schema import RunRow, utcnow
from agent.models.product import Product
from agent.pipeline.nodes.draft import draft_node
from agent.pipeline.nodes.parse import parse_node
from agent.pipeline.nodes.publish import publish_node
from agent.pipeline.nodes.validate import ValidatedProduct, validate_node


@dataclass
class PipelineResult:
    facts: ValidatedProduct
    description: str
    product: Product | None = None
    total_cost: Decimal = field(default_factory=lambda: Decimal("0"))


async def run_pipeline(
    raw_text: str,
    session: AsyncSession,
    *,
    publish: bool = False,
    llm: AzureLLMClient | None = None,
) -> PipelineResult:
    started_at = utcnow()
    facts = await parse_node(raw_text, session, llm=llm)
    validated = await validate_node(facts, session)
    description = await draft_node(validated, session, llm=llm)

    product: Product | None = None
    total_cost = Decimal("0")

    if publish:
        product = await publish_node(validated, description, session)
        await session.execute(
            update(RunRow)
            .where(RunRow.product_id.is_(None), RunRow.created_at >= started_at)
            .values(product_id=product.id)
        )
        await session.commit()
        total_cost = await total_cost_for_product(session, product.id)

    return PipelineResult(
        facts=validated,
        description=description,
        product=product,
        total_cost=total_cost,
    )
