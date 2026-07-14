from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from agent.mcp.client import get_storefront_client
from agent.models.product import Product, ProductFacts
from agent.pipeline.nodes.validate import ValidatedProduct


async def publish_node(
    product: ValidatedProduct,
    description: str,
    session: AsyncSession,
) -> Product:
    """Publish through the MCP storefront client (inline tool dispatch by default)."""
    _ = session
    client = get_storefront_client()
    facts = ProductFacts(
        name=product.name,
        price=product.price,
        category=product.category,
        features=product.features,
        ingredients=product.ingredients,
        materials=product.materials,
        photo_filename=product.photo_filename,
    )
    published = await client.create_and_publish(
        name=product.name,
        price=str(product.price),
        category=product.category,
        description=description,
        facts=facts.model_dump(mode="json"),
    )
    return Product.model_validate(published)


async def publish_rewrite_node(*, product_id: int, description: str) -> Product:
    client = get_storefront_client()
    updated = await client.update_listing(product_id=product_id, description=description)
    return Product.model_validate(updated)
