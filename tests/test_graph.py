import os
import uuid

os.environ["LLM_MOCK"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlalchemy import func, select

from agent.audit.service import log_feedback
from agent.db.schema import ApprovalRow, FeedbackEventRow
from agent.db.session import SessionLocal, init_db
from agent.pipeline.session import AgentSession


@pytest.fixture
async def agent_session():
    await init_db()
    async with AsyncSqliteSaver.from_conn_string(":memory:") as checkpointer:
        yield AgentSession(checkpointer)


@pytest.mark.asyncio
async def test_gate_revision_and_publish(agent_session: AgentSession):
    unique = uuid.uuid4().hex[:8]
    raw = f"name: Zenith Earbuds {unique}, Rs 2499, electronics, 8-hour battery, ANC, photo: test.jpg"

    thread_id, gate = await agent_session.start(raw)
    assert gate["type"] == "gate"
    assert gate["description"]

    gate2 = await agent_session.resume(
        thread_id,
        {"action": "reject", "comment": "make it shorter"},
    )
    assert gate2["type"] == "gate"
    assert gate2["draft_num"] >= 2
    assert gate2["description"] != gate["description"]

    final = await agent_session.resume(thread_id, {"action": "approve"})
    assert final["type"] == "complete"
    assert final["status"] == "published"
    assert final["product_id"] is not None


@pytest.mark.asyncio
async def test_gate_edit_and_redraft(agent_session: AgentSession):
    unique = uuid.uuid4().hex[:8]
    raw = f"name: Edit Mug {unique}, Rs 499, kitchen, ceramic, 350ml"

    thread_id, gate = await agent_session.start(raw)
    edited = gate["description"] + " Hand-thrown finish."
    gate2 = await agent_session.resume(
        thread_id,
        {
            "action": "reject",
            "comment": "add hand-thrown detail",
            "edited_description": edited,
        },
    )
    assert gate2["type"] == "gate"
    assert "Hand-thrown finish" in gate2["description"]


@pytest.mark.asyncio
async def test_audit_trail_on_revision(agent_session: AgentSession):
    unique = uuid.uuid4().hex[:8]
    raw = f"name: Audit Mug {unique}, Rs 499, kitchen, ceramic, 350ml"

    thread_id, _ = await agent_session.start(raw)
    await agent_session.resume(thread_id, {"action": "reject", "comment": "too formal"})
    await agent_session.resume(thread_id, {"action": "approve"})

    async with SessionLocal() as session:
        feedback_count = await session.execute(select(func.count()).select_from(FeedbackEventRow))
        approval_count = await session.execute(select(func.count()).select_from(ApprovalRow))
        assert feedback_count.scalar_one() >= 1
        assert approval_count.scalar_one() >= 1


@pytest.mark.asyncio
async def test_missing_price_pauses_for_facts(agent_session: AgentSession):
    raw = (
        "Model Name iPhone Test Pro | Smartphone Yes | "
        "Operating System iOS 26 | dual camera"
    )

    thread_id, payload = await agent_session.start(raw)
    assert payload["type"] == "needs_facts"
    assert any(issue["field"] == "price" for issue in payload["issues"])

    gate = await agent_session.resume(
        thread_id,
        {"price": "99999", "category": "electronics"},
    )
    assert gate["type"] == "gate"
    assert gate["description"]


@pytest.mark.asyncio
async def test_max_revisions_parks(agent_session: AgentSession):
    unique = uuid.uuid4().hex[:8]
    raw = f"name: Park Lamp {unique}, Rs 3299, electronics, LED desk lamp, touch dimmer"

    thread_id, _ = await agent_session.start(raw)
    result = {"type": "gate"}
    for _ in range(6):
        if result.get("type") == "complete":
            break
        result = await agent_session.resume(
            thread_id,
            {"action": "reject", "comment": "still not right"},
        )

    assert result["type"] == "complete"
    assert result["status"] == "parked"
