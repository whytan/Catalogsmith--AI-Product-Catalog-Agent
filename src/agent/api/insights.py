from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.templating import Jinja2Templates

from agent.config import settings
from agent.db.session import get_session
from agent.metrics.loop2 import loop2_summary, persona_dashboard
from agent.personas.conflicts import detect_loop_conflicts

router = APIRouter(tags=["insights"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "web" / "templates"
TEMPLATES = Jinja2Templates(directory=str(TEMPLATES_DIR))
TEMPLATES.env.globals["store_name"] = settings.store_name


@router.get("/insights", response_class=HTMLResponse)
async def insights_home(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    personas = await persona_dashboard(session)
    return TEMPLATES.TemplateResponse(
        request,
        "insights/index.html",
        {"personas": personas},
    )


@router.get("/insights/personas", response_class=HTMLResponse)
async def insights_personas(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    data = await persona_dashboard(session)
    return TEMPLATES.TemplateResponse(
        request,
        "insights/personas.html",
        {"data": data},
    )


@router.get("/insights/mining", response_class=HTMLResponse)
async def insights_mining(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    data = await loop2_summary(session)
    conflicts = []
    if data["personas"]["clusters"]:
        top = data["personas"]["clusters"][0]
        conflicts = await detect_loop_conflicts(session, product_id=top["product_id"])
    return TEMPLATES.TemplateResponse(
        request,
        "insights/mining.html",
        {"data": data, "conflicts": conflicts},
    )
