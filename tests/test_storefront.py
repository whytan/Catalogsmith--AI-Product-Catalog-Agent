import pytest
from httpx import ASGITransport, AsyncClient

from agent.db.session import SessionLocal, init_db
from agent.main import app
from agent.seed import seed_if_empty


@pytest.fixture
async def client():
    await init_db()
    async with SessionLocal() as session:
        await seed_if_empty(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["weekend"] == 8
    assert data["loop2"]["synthetic"] is True
    assert data["mcp"]["tools"] == 9


@pytest.mark.asyncio
async def test_storefront_lists_seeded_products(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "Aurora Wireless Earbuds" in response.text
    assert "/static/products/aurora-earbuds.jpg" in response.text
    assert 'class="product-photo"' in response.text


@pytest.mark.asyncio
async def test_api_products(client):
    response = await client.get("/api/products?status=published")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 12
