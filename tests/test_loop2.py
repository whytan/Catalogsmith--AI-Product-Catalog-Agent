import os
import uuid

os.environ["LLM_MOCK"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent.adapter.sqlite import SQLiteStorefrontAdapter
from agent.db.session import SessionLocal, init_db
from agent.models.product import ProductCreate, ProductStatus
from agent.personas.miner import mine_signal_clusters, propose_rewrite, question_frequency
from agent.personas.orchestrate import Loop2Error, run_loop2_flow
from agent.personas.panel import run_persona_panel, seed_personas
from agent.personas.profiles import load_persona_profiles
from agent.pipeline.session import AgentSession
from agent.seed import seed_if_empty


@pytest.fixture
async def seeded_session():
    await init_db()
    async with SessionLocal() as session:
        await seed_if_empty(session)
        await seed_personas(session)
        yield session


@pytest.mark.asyncio
async def test_persona_profiles_loaded():
    profiles = load_persona_profiles()
    assert len(profiles) == 4
    assert {profile.persona_id for profile in profiles} == {
        "bargain_hunter",
        "spec_reader",
        "skeptical_gifter",
        "skimmer",
    }


@pytest.mark.asyncio
async def test_persona_panel_creates_signals(seeded_session):
    result = await run_persona_panel(seeded_session, limit=2, seed=7)
    assert result["synthetic"] is True
    assert result["signals_created"] > 0
    assert result["products"] == 2


@pytest.mark.asyncio
async def test_signal_miner_clusters_questions(seeded_session):
    await run_persona_panel(seeded_session, limit=2, seed=11)
    clusters = await mine_signal_clusters(seeded_session)
    assert clusters
    assert clusters[0].theme


@pytest.mark.asyncio
async def test_rewrite_proposal_for_theme(seeded_session):
    await run_persona_panel(seeded_session, limit=1, seed=3)
    adapter = SQLiteStorefrontAdapter(seeded_session)
    products = await adapter.list_products(status=ProductStatus.PUBLISHED.value)
    proposal = await propose_rewrite(seeded_session, products[0].id, "battery")
    assert proposal["synthetic"] is True
    assert proposal["proposed_description"] != proposal["current_description"] or "battery" in proposal["proposed_description"].lower()


@pytest.mark.asyncio
async def test_rewrite_gate_flow(seeded_session):
    await run_persona_panel(seeded_session, limit=1, seed=5)
    adapter = SQLiteStorefrontAdapter(seeded_session)
    products = await adapter.list_products(status=ProductStatus.PUBLISHED.value)
    product = products[0]
    clusters = await mine_signal_clusters(seeded_session, product_id=product.id)
    assert clusters
    theme = clusters[0].theme
    before = await question_frequency(seeded_session, product_id=product.id, theme=theme)
    proposal = await propose_rewrite(seeded_session, product.id, theme)

    async with AsyncSqliteSaver.from_conn_string(":memory:") as checkpointer:
        agent = AgentSession(checkpointer)
        thread_id, gate = await agent.start_rewrite(
            product_id=product.id,
            proposed_description=proposal["proposed_description"],
            reason=proposal["reason"],
        )
        assert gate["type"] == "gate"
        assert gate["rewrite_reason"]
        final = await agent.resume(thread_id, {"action": "approve"})
        assert final["type"] == "complete"
        assert final["product_id"] == product.id

    assert before >= 1


@pytest.mark.asyncio
async def test_loop2_orchestration(seeded_session):
    async with AsyncSqliteSaver.from_conn_string(":memory:") as checkpointer:
        agent = AgentSession(checkpointer)
        result = await run_loop2_flow(seeded_session, agent, limit=2, panel_seed=9)
        assert result["synthetic"] is True
        assert result["panel"]["signals_created"] > 0
        assert result["thread_id"]
        assert result["gate"]["type"] == "gate"
        assert result["gate_url"] == f"/app?thread={result['thread_id']}"
        assert result["cluster"]["theme"]


@pytest.mark.asyncio
async def test_loop2_run_api():
    await init_db()
    async with SessionLocal() as session:
        await seed_if_empty(session)
        await seed_personas(session)

    async with AsyncSqliteSaver.from_conn_string(":memory:") as checkpointer:
        from httpx import ASGITransport, AsyncClient

        from agent.main import app

        app.state.agent_session = AgentSession(checkpointer)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/personas/loop2/run?limit=2")
            assert response.status_code == 200
            data = response.json()
            assert data["gate"]["rewrite_reason"]
            assert data["gate_url"].startswith("/app?thread=")


@pytest.mark.asyncio
async def test_loop2_orchestration_requires_products():
    await init_db()
    async with SessionLocal() as session:
        await seed_personas(session)
        async with AsyncSqliteSaver.from_conn_string(":memory:") as checkpointer:
            agent = AgentSession(checkpointer)
            with pytest.raises(Loop2Error):
                await run_loop2_flow(session, agent, limit=2, panel_seed=1)
