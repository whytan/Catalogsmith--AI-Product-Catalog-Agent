from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from agent.config import settings

router = APIRouter(tags=["pages"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "web" / "templates"
TEMPLATES = Jinja2Templates(directory=str(TEMPLATES_DIR))
TEMPLATES.env.globals["store_name"] = settings.store_name


@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return TEMPLATES.TemplateResponse(request, "about/index.html", {})
