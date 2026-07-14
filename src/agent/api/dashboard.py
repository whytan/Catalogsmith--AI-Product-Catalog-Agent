from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.templating import Jinja2Templates

from agent.config import settings
from agent.db.session import get_session
from agent.metrics.guardrails import guardrails_summary
from agent.metrics.learning import learning_summary
from agent.metrics.loop2 import loop2_summary, persona_dashboard

router = APIRouter(tags=["dashboard"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "web" / "templates"
TEMPLATES = Jinja2Templates(directory=str(TEMPLATES_DIR))
TEMPLATES.env.globals["store_name"] = settings.store_name


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_home(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    learning = await learning_summary(session)
    guardrails = await guardrails_summary(session)
    personas = await persona_dashboard(session)
    return TEMPLATES.TemplateResponse(
        request,
        "dashboard/index.html",
        {
            "learning": learning,
            "guardrails": guardrails,
            "personas": personas,
        },
    )


@router.get("/dashboard/learning", response_class=HTMLResponse)
async def dashboard_learning(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    data = await learning_summary(session)
    return TEMPLATES.TemplateResponse(
        request,
        "dashboard/learning.html",
        {"data": data},
    )


@router.get("/api/dashboard/learning")
async def api_learning_summary(session: AsyncSession = Depends(get_session)):
    return await learning_summary(session)


@router.get("/dashboard/guardrails", response_class=HTMLResponse)
async def dashboard_guardrails(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    data = await guardrails_summary(session)
    return TEMPLATES.TemplateResponse(
        request,
        "dashboard/guardrails.html",
        {"data": data},
    )


@router.get("/api/dashboard/guardrails")
async def api_guardrails_summary(session: AsyncSession = Depends(get_session)):
    return await guardrails_summary(session)


@router.get("/dashboard/personas")
async def dashboard_personas_redirect():
    return RedirectResponse(url="/insights/personas", status_code=301)


@router.get("/dashboard/loop2")
async def dashboard_loop2_redirect():
    return RedirectResponse(url="/insights/mining", status_code=301)


@router.get("/api/dashboard/personas")
async def api_persona_dashboard(session: AsyncSession = Depends(get_session)):
    return await persona_dashboard(session)


@router.get("/api/dashboard/loop2")
async def api_loop2_dashboard(session: AsyncSession = Depends(get_session)):
    return await loop2_summary(session)
