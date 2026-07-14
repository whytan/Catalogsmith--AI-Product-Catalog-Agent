import os

os.environ["LLM_MOCK"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import pytest
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent.db.session import SessionLocal, init_db
from agent.main import app
from agent.pipeline.session import AgentSession
from agent.seed import seed_if_empty


@pytest.fixture
async def client():
    await init_db()
    async with SessionLocal() as session:
        await seed_if_empty(session)

    async with AsyncSqliteSaver.from_conn_string(":memory:") as checkpointer:
        app.state.agent_session = AgentSession(checkpointer)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.mark.asyncio
async def test_agent_app_page(client):
    response = await client.get("/app")
    assert response.status_code == 200
    assert "Approval gate" in response.text


@pytest.mark.asyncio
async def test_health_weekend_5(client):
    response = await client.get("/health")
    assert response.json()["weekend"] == 8


@pytest.mark.asyncio
async def test_about_page(client):
    response = await client.get("/about")
    assert response.status_code == 200
    assert "Two feedback loops" in response.text
    assert "Try the agent" in response.text


@pytest.mark.asyncio
async def test_insights_home(client):
    response = await client.get("/insights")
    assert response.status_code == 200
    assert "Customer insights" in response.text
    assert "SYNTHETIC" in response.text
    assert "Run Loop 2" in response.text


@pytest.mark.asyncio
async def test_shop_uses_customer_nav(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "Seller login" in response.text
    assert "How it works" in response.text
    # Shop nav should not expose seller dashboard directly
    assert 'href="/dashboard"' not in response.text.split("header-nav")[1].split("</nav>")[0]


@pytest.mark.asyncio
async def test_legacy_insights_redirects(client):
    personas = await client.get("/dashboard/personas", follow_redirects=False)
    assert personas.status_code == 301
    assert personas.headers["location"] == "/insights/personas"

    mining = await client.get("/dashboard/loop2", follow_redirects=False)
    assert mining.status_code == 301
    assert mining.headers["location"] == "/insights/mining"
