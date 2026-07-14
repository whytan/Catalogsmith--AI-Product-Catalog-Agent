import uuid

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent.memory.feedback_store import add_feedback_memory, retrieve_feedback_memories
from agent.memory.voice_store import retrieve_voice_rules, seed_voice_collection
from agent.pipeline.session import AgentSession


@pytest.mark.asyncio
async def test_voice_collection_seeded():
    seed_voice_collection()
    rules = retrieve_voice_rules(category="electronics", limit=5)
    assert len(rules) >= 1


@pytest.mark.asyncio
async def test_feedback_memory_retrieval_by_category():
    add_feedback_memory(
        category="electronics",
        before="Long draft",
        after="Long draft",
        comment="shorter",
        thread_id="t-1",
    )
    add_feedback_memory(
        category="kitchen",
        before="Another draft",
        after="Another draft",
        comment="more formal",
        thread_id="t-2",
    )

    memories = retrieve_feedback_memories(
        category="electronics",
        query="wireless earbuds electronics",
        limit=5,
    )
    assert any("shorter" in memory.lower() for memory in memories)


@pytest.mark.asyncio
async def test_learning_edit_rate_declines_with_consistent_feedback():
    async with AsyncSqliteSaver.from_conn_string(":memory:") as checkpointer:
        agent = AgentSession(checkpointer)
        rates: list[int] = []

        for index in range(3):
            unique = uuid.uuid4().hex[:8]
            raw = f"name: Learn Buds {unique}, Rs 2499, electronics, 8-hour battery, ANC"
            thread_id, gate = await agent.start(raw)
            assert gate["type"] == "gate"

            revisions = 0
            if index == 0:
                revisions = 2
            elif index == 1:
                revisions = 1

            for _ in range(revisions):
                gate = await agent.resume(
                    thread_id,
                    {"action": "reject", "comment": "shorter, no exclamation marks"},
                )
                assert gate["type"] == "gate"

            final = await agent.resume(thread_id, {"action": "approve"})
            assert final["status"] == "published"
            rates.append(revisions)

        assert rates[0] >= rates[1] >= rates[2]
