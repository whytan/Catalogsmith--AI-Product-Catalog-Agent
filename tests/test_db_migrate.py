import pytest
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent.audit.service import log_feedback
from agent.db.migrate import apply_sqlite_migrations
from agent.pipeline.messages import coerce_chat_message, serialize_messages


def test_coerce_human_message():
    assert coerce_chat_message(HumanMessage(content="hello")) == {
        "role": "user",
        "content": "hello",
    }


def test_coerce_ai_message():
    assert coerce_chat_message(AIMessage(content="draft ready")) == {
        "role": "assistant",
        "content": "draft ready",
    }


def test_coerce_dict_message():
    assert coerce_chat_message({"role": "assistant", "content": "ok"}) == {
        "role": "assistant",
        "content": "ok",
    }


def test_serialize_messages_mixed():
    messages = serialize_messages(
        [
            HumanMessage(content="facts"),
            {"role": "assistant", "content": "parsed"},
            AIMessage(content="draft"),
        ]
    )
    assert messages[0]["role"] == "user"
    assert messages[1]["content"] == "parsed"
    assert messages[2]["role"] == "assistant"


@pytest.mark.asyncio
async def test_migrate_adds_feedback_event_columns(tmp_path):
    db_path = tmp_path / "legacy.db"
    sync_engine = create_engine(f"sqlite:///{db_path}")
    with sync_engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE feedback_events (
                    id INTEGER PRIMARY KEY,
                    product_id INTEGER,
                    type VARCHAR(50),
                    "before" TEXT,
                    "after" TEXT,
                    comment TEXT,
                    created_at DATETIME
                )
                """
            )
        )
    sync_engine.dispose()

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with async_engine.begin() as conn:
        await conn.run_sync(apply_sqlite_migrations)

    SessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)
    async with SessionLocal() as session:
        row = await log_feedback(
            session,
            event_type="comment",
            before="before",
            after="before",
            comment="shorter",
            thread_id="thread-1",
            category="electronics",
        )
        assert row.thread_id == "thread-1"
        assert row.category == "electronics"

    await async_engine.dispose()
