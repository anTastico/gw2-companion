from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates


APP_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

router = APIRouter()


@router.get("/app", name="web_dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "page_title": "Dashboard",
            "app_version": "0.1.0",
        },
    )
