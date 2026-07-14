import os
import uuid

os.environ["LLM_MOCK"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["CHROMA_EPHEMERAL"] = "1"

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlalchemy import func, select

from agent.db.schema import FeedbackEventRow
from agent.db.session import SessionLocal, init_db
from agent.metrics.learning import learning_summary
from agent.pipeline.session import AgentSession


@pytest.mark.asyncio
async def test_learning_summary_after_publish():
    await init_db()
    async with AsyncSqliteSaver.from_conn_string(":memory:") as checkpointer:
        agent = AgentSession(checkpointer)
        unique = uuid.uuid4().hex[:8]
        raw = f"name: Metrics Mug {unique}, Rs 499, kitchen, ceramic, 350ml"
        thread_id, _ = await agent.start(raw)
        await agent.resume(thread_id, {"action": "reject", "comment": "shorter"})
        await agent.resume(thread_id, {"action": "approve"})

    async with SessionLocal() as session:
        summary = await learning_summary(session)
        assert summary["summary"]["products"] == 1
        assert summary["points"][0]["edit_rate"] == 1

        snapshots = await session.execute(
            select(func.count()).select_from(FeedbackEventRow).where(
                FeedbackEventRow.type == "publish_snapshot"
            )
        )
        assert snapshots.scalar_one() == 1
