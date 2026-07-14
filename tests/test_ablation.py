import os

os.environ["LLM_MOCK"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["CHROMA_EPHEMERAL"] = "1"

import pytest

from agent.db.session import SessionLocal, init_db
from agent.memory.chroma import reset_client
from agent.pipeline.nodes.validate import ValidatedProduct
from decimal import Decimal

from eval.ablation import run_ablation, run_arm
from eval.fixtures import ABLATION_PRODUCTS


@pytest.fixture
async def ablation_session():
    await init_db()
    reset_client()
    async with SessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_ablation_memory_on_beats_off(ablation_session):
    """Causal proof: ON arm should need fewer rubric-gated redrafts on average."""
    subset = ABLATION_PRODUCTS[:4]
    report = await run_ablation(ablation_session, products=subset)
    assert report.memory_off.mean_edit_rate > report.memory_on.mean_edit_rate
    assert report.memory_reduced_edits is True
    assert report.delta_mean_edit_rate > 0


@pytest.mark.asyncio
async def test_ablation_off_arm_repeats_mistakes_on_later_products(ablation_session):
    off = await run_arm(ablation_session, ABLATION_PRODUCTS[:3], memory_on=False)
    # Without memory, later products still need multiple cycles (no cross-product learning).
    assert off.products[0].edit_rate >= 1
    assert off.products[-1].edit_rate >= 1


@pytest.mark.asyncio
async def test_memory_off_setting_skips_feedback_storage():
    from agent.config import settings
    from agent.memory import store_feedback_in_memory
    from agent.memory.chroma import get_collection, reset_client
    from agent.memory.feedback_store import FEEDBACK_COLLECTION

    reset_client()
    original = settings.memory_off
    settings.memory_off = True
    try:
        store_feedback_in_memory(
            category="electronics",
            before="before",
            after="after",
            comment="no exclamation marks",
            thread_id="t1",
        )
        collection = get_collection(FEEDBACK_COLLECTION)
        assert collection.count() == 0
    finally:
        settings.memory_off = original
