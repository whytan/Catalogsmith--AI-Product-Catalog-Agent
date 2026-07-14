import io
import os

os.environ["LLM_MOCK"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import pytest
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent.db.session import SessionLocal, init_db
from agent.main import app
from agent.models.product import ProductFacts
from agent.pipeline.graph import parse_state
from agent.pipeline.session import AgentSession
from agent.seed import seed_if_empty
from agent.web.catalog_images import PRODUCTS_DIR, product_image_url


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
async def test_upload_product_image_endpoint(client):
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\x0d\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    files = {"file": ("demo-phone.png", io.BytesIO(png_bytes), "image/png")}
    response = await client.post("/api/agent/upload-image", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["filename"].endswith(".png")
    assert data["url"].startswith("/static/products/")
    assert product_image_url(data["filename"]) == data["url"]


@pytest.mark.asyncio
async def test_parse_state_attaches_seller_photo():
    state = {
        "raw_text": "name: Demo Phone, Rs 9999, electronics, 5G",
        "seller_photo_filename": "demo-phone.png",
    }
    result = await parse_state(state)
    facts = ProductFacts.model_validate(result["facts"])
    assert facts.photo_filename == "demo-phone.png"


@pytest.mark.asyncio
async def test_attach_photo_updates_gate(client):
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\x0d\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    files = {"file": ("attach-test.png", io.BytesIO(png_bytes), "image/png")}
    upload = await client.post("/api/agent/upload-image", files=files)
    filename = upload.json()["filename"]

    agent: AgentSession = app.state.agent_session
    thread_id, gate = await agent.start("name: Photo Mug abc, Rs 499, kitchen, ceramic")
    assert gate["type"] == "gate"

    updated = await agent.attach_photo(thread_id, filename)
    assert updated["type"] == "gate"
    assert updated["facts"]["photo_filename"] == filename
    assert product_image_url(filename) is not None

    for path in PRODUCTS_DIR.glob("attach-test-*.png"):
        path.unlink(missing_ok=True)
    for path in PRODUCTS_DIR.glob("demo-phone-*.png"):
        path.unlink(missing_ok=True)
