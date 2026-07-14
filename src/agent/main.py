from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent.api.agent import router as agent_router
from agent.api.dashboard import router as dashboard_router
from agent.api.insights import router as insights_router
from agent.api.pages import router as pages_router
from agent.api.personas import router as personas_router
from agent.api.storefront import router as storefront_router
from agent.config import settings
from agent.db.session import SessionLocal, init_db
from agent.memory.chroma import reset_client
from agent.memory.voice_store import seed_voice_collection
from agent.pipeline.session import AgentSession
from agent.personas.panel import seed_personas
from agent.seed import seed_if_empty

STATIC_DIR = Path(__file__).resolve().parent / "web" / "static"
CHECKPOINT_DB = Path("data/checkpoints.db")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    CHECKPOINT_DB.parent.mkdir(parents=True, exist_ok=True)
    reset_client()
    seeded_voice = seed_voice_collection()
    if seeded_voice:
        print(f"Seeded {seeded_voice} voice rules into Chroma.")

    async with AsyncSqliteSaver.from_conn_string(str(CHECKPOINT_DB)) as checkpointer:
        async with SessionLocal() as session:
            seeded = await seed_if_empty(session)
            if seeded:
                print(f"Seeded {seeded} demo products.")
            seeded_personas = await seed_personas(session)
            if seeded_personas:
                print(f"Seeded {seeded_personas} SYNTHETIC personas.")

        app.state.agent_session = AgentSession(checkpointer)
        yield


app = FastAPI(
    title="Catalogsmith",
    description="AI catalog agent — parse, draft, approve, publish",
    version="0.8.0",
    lifespan=lifespan,
)

app.include_router(storefront_router)
app.include_router(pages_router)
app.include_router(agent_router)
app.include_router(dashboard_router)
app.include_router(insights_router)
app.include_router(personas_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "store": settings.store_name,
        "version": "0.8.0",
        "weekend": 8,
        "loop2": {"synthetic": True},
        "mcp": {
            "tools": 9,
            "mode": settings.mcp_mode,
            "server_command": "catalogsmith-mcp",
        },
    }
