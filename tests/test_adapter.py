import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agent.adapter.sqlite import (
    ConflictError,
    NotFoundError,
    SQLiteStorefrontAdapter,
)
from agent.db.session import SessionLocal, init_db
from agent.models.product import ProductCreate, ProductFacts, ProductStatus


@pytest.fixture
async def session() -> AsyncSession:
    await init_db()
    async with SessionLocal() as session:
        yield session


@pytest.fixture
def adapter(session: AsyncSession) -> SQLiteStorefrontAdapter:
    return SQLiteStorefrontAdapter(session)


@pytest.mark.asyncio
async def test_create_and_get(adapter: SQLiteStorefrontAdapter) -> None:
    payload = ProductCreate(
        name="Test Kettle",
        price="999.00",
        category="kitchen",
        description="A test kettle.",
        facts=ProductFacts(features=["1L capacity"]),
        status=ProductStatus.DRAFT,
    )
    created = await adapter.create_product(payload)
    assert created.id > 0
    assert created.status == ProductStatus.DRAFT

    fetched = await adapter.get_product(created.id)
    assert fetched is not None
    assert fetched.name == "Test Kettle"


@pytest.mark.asyncio
async def test_publish_unpublish(adapter: SQLiteStorefrontAdapter) -> None:
    created = await adapter.create_product(
        ProductCreate(name="Publish Me", price="100.00", category="beauty")
    )
    published = await adapter.publish(created.id)
    assert published.status == ProductStatus.PUBLISHED

    unpublished = await adapter.unpublish(created.id)
    assert unpublished.status == ProductStatus.DRAFT


@pytest.mark.asyncio
async def test_duplicate_name_rejected(adapter: SQLiteStorefrontAdapter) -> None:
    payload = ProductCreate(name="Unique Mug", price="50.00", category="kitchen")
    await adapter.create_product(payload)
    with pytest.raises(ConflictError):
        await adapter.create_product(payload)


@pytest.mark.asyncio
async def test_invalid_category_rejected() -> None:
    with pytest.raises(Exception):
        ProductCreate(name="Bad Cat", price="10.00", category="spaceships")


@pytest.mark.asyncio
async def test_search_products(adapter: SQLiteStorefrontAdapter) -> None:
    await adapter.create_product(
        ProductCreate(
            name="Aurora Earbuds",
            price="2499.00",
            category="electronics",
            description="Wireless earbuds with ANC",
            status=ProductStatus.PUBLISHED,
        )
    )
    await adapter.create_product(
        ProductCreate(
            name="Bamboo Board",
            price="899.00",
            category="kitchen",
            description="Cutting board",
            status=ProductStatus.PUBLISHED,
        )
    )
    results = await adapter.search_products("earbuds", status=ProductStatus.PUBLISHED.value)
    assert len(results) == 1
    assert results[0].name == "Aurora Earbuds"


@pytest.mark.asyncio
async def test_delete_product(adapter: SQLiteStorefrontAdapter) -> None:
    created = await adapter.create_product(
        ProductCreate(name="Delete Me", price="10.00", category="kitchen")
    )
    assert await adapter.delete_product(created.id) is True
    assert await adapter.get_product(created.id) is None


@pytest.mark.asyncio
async def test_get_categories(adapter: SQLiteStorefrontAdapter) -> None:
    categories = await adapter.get_categories()
    assert categories == ["beauty", "electronics", "kitchen"]


@pytest.mark.asyncio
async def test_not_found(adapter: SQLiteStorefrontAdapter) -> None:
    with pytest.raises(NotFoundError):
        await adapter.publish(9999)
