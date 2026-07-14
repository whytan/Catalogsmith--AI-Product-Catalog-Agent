import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agent.db.session import SessionLocal, init_db
from agent.mcp.client import StorefrontMCPClient
from agent.mcp.tools import TOOL_NAMES, dispatch_tool
from agent.models.product import ProductStatus


@pytest.fixture
async def session() -> AsyncSession:
    await init_db()
    async with SessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_mcp_tool_names() -> None:
    assert len(TOOL_NAMES) == 9


@pytest.mark.asyncio
async def test_mcp_create_get_publish(session: AsyncSession) -> None:
    created = await dispatch_tool(
        session,
        "create_product",
        {
            "name": "MCP Test Lamp",
            "price": "2199.00",
            "category": "electronics",
            "description": "LED desk lamp",
            "status": "draft",
        },
    )
    assert created["name"] == "MCP Test Lamp"

    fetched = await dispatch_tool(session, "get_product", {"product_id": created["id"]})
    assert fetched["id"] == created["id"]

    published = await dispatch_tool(session, "publish", {"product_id": created["id"]})
    assert published["status"] == ProductStatus.PUBLISHED.value


@pytest.mark.asyncio
async def test_mcp_list_search_categories_delete(session: AsyncSession) -> None:
    await dispatch_tool(
        session,
        "create_product",
        {
            "name": "MCP Search Mug",
            "price": "499.00",
            "category": "kitchen",
            "description": "Ceramic mug for morning coffee",
            "status": "published",
        },
    )

    categories = await dispatch_tool(session, "get_categories", {})
    assert categories["categories"] == ["beauty", "electronics", "kitchen"]

    listed = await dispatch_tool(session, "list_products", {"status": "published"})
    assert listed["total"] >= 1

    search = await dispatch_tool(session, "search_products", {"query": "mug", "status": "published"})
    assert search["total"] >= 1

    product_id = search["products"][0]["id"]
    unpublished = await dispatch_tool(session, "unpublish", {"product_id": product_id})
    assert unpublished["status"] == ProductStatus.DRAFT.value

    deleted = await dispatch_tool(session, "delete_product", {"product_id": product_id})
    assert deleted["deleted"] is True


@pytest.mark.asyncio
async def test_mcp_client_create_and_publish() -> None:
    client = StorefrontMCPClient(mode="inline")
    published = await client.create_and_publish(
        name="MCP Client Jar",
        price="449.00",
        category="kitchen",
        description="Airtight spice jar",
        facts={"name": "MCP Client Jar", "features": ["glass", "airtight"]},
    )
    assert published["status"] == ProductStatus.PUBLISHED.value
    assert published["name"] == "MCP Client Jar"


@pytest.mark.asyncio
async def test_publish_node_uses_mcp_client(session: AsyncSession) -> None:
    from decimal import Decimal

    from agent.pipeline.nodes.publish import publish_node
    from agent.pipeline.nodes.validate import ValidatedProduct

    product = ValidatedProduct(
        name="Publish Via MCP",
        price=Decimal("1299.00"),
        category="electronics",
        features=["USB-C charging"],
    )
    published = await publish_node(product, "Compact charger with USB-C.", session)
    assert published.status == ProductStatus.PUBLISHED
    assert published.name == "Publish Via MCP"
