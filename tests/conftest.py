import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["LLM_MOCK"] = "1"
os.environ["CHROMA_EPHEMERAL"] = "1"

import pytest
from agent.db.migrate import apply_sqlite_migrations
from agent.db.schema import Base
from agent.db.session import engine, init_db
from agent.memory.chroma import reset_client
from agent.memory.voice_store import seed_voice_collection


@pytest.fixture(autouse=True)
async def fresh_db():
    """Isolate each test with an empty database schema."""
    reset_client()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(apply_sqlite_migrations)
    seed_voice_collection()
    yield
