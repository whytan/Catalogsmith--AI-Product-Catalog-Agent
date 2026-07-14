import os
import uuid

os.environ["LLM_MOCK"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent.pipeline.session import AgentSession


@pytest.fixture
async def agent_session():
    from agent.db.session import init_db

    await init_db()
    async with AsyncSqliteSaver.from_conn_string(":memory:") as checkpointer:
        yield AgentSession(checkpointer)


@pytest.mark.asyncio
async def test_gate_surfaces_grounding_violations(agent_session: AgentSession):
    unique = uuid.uuid4().hex[:8]
    raw = f"name: Grounding Demo Buds {unique}, Rs 2499, electronics, 8-hour battery, ANC"

    thread_id, gate = await agent_session.start(raw)
    assert gate["type"] == "gate"
    assert gate["grounding_violations"]
    assert any(item["claim"] == "waterproof" for item in gate["grounding_violations"])
