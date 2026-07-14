import os

os.environ["LLM_MOCK"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import pytest
from sqlalchemy import func, select

from agent.config import settings
from agent.db.schema import RunRow
from agent.db.session import SessionLocal, init_db
from agent.pipeline.runner import run_pipeline


@pytest.fixture(autouse=True)
def ensure_mock_mode():
    assert settings.llm_mock is True


@pytest.mark.asyncio
async def test_pipeline_publish_logs_cost():
    await init_db()
    async with SessionLocal() as session:
        raw = (
            "Weekend CLI Speaker, ₹3499, electronics, "
            "12-hour battery, bluetooth 5.3, photo: weekend-speaker.jpg"
        )
        result = await run_pipeline(raw, session, publish=True)

        assert result.product is not None
        assert result.product.status.value == "published"
        assert result.description
        assert result.total_cost > 0

        count = await session.execute(
            select(func.count()).select_from(RunRow).where(RunRow.product_id == result.product.id)
        )
        assert count.scalar_one() >= 2  # parse + draft


@pytest.mark.asyncio
async def test_pipeline_dry_run_no_product():
    await init_db()
    async with SessionLocal() as session:
        raw = "Draft Only Mug, ₹499, kitchen, ceramic body, 350ml"
        result = await run_pipeline(raw, session, publish=False)
        assert result.product is None
