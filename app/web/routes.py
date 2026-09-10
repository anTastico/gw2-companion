from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.services.account_state import AccountState
from app.services.gw2_api import GW2Client
from app.trackers.aurora import AuroraTracker
from app.trackers.vision import VisionTracker
from app.trackers.regalia import RegaliaTracker


APP_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

router = APIRouter()

gw2 = GW2Client()
aurora = AuroraTracker()
vision = VisionTracker()
regalia = RegaliaTracker()


def _progress(current: int, maximum: int) -> dict:
    percent = round(current / maximum * 100, 1) if maximum else 0

    return {
        "current": current,
        "max": maximum,
        "percent": percent,
    }


def _goal_card(
    *,
    key: str,
    name: str,
    current: int,
    maximum: int,
    status: str,
    description: str,
) -> dict:
    progress = _progress(current, maximum)

    badge_class = ""
    badge_label = "Tracked"

    if status == "completed":
        badge_class = "badge-complete"
        badge_label = "Complete"
    elif status == "in_progress":
        badge_class = "badge-active"
        badge_label = "Active"
    elif status == "locked":
        badge_label = "Locked"

    return {
        "key": key,
        "name": name,
        "status": status,
        "badge_label": badge_label,
        "badge_class": badge_class,
        "description": description,
        **progress,
    }


@router.get("/app", name="web_dashboard")
async def dashboard(request: Request):
    account_state = await AccountState.load(client=gw2)

    account = await gw2.get_account()

    aurora_progress = await aurora.progress(
        account_state=account_state
    )
    vision_progress = await vision.progress(
        account_state=account_state
    )
    regalia_progress = await regalia.progress(
        account_state=account_state
    )

    aurora_summary = aurora_progress["summary"]
    aurora_achievement = aurora_summary["achievement_progress"]

    vision_summary = vision_progress["summary"]
    vision_achievement = vision_summary["achievement_progress"]

    regalia_status = (
        "completed"
        if regalia_progress["completed"] >= regalia_progress["total"]
        else "in_progress"
    )

    goals = [
        _goal_card(
            key="aurora",
            name="Aurora",
            current=aurora_achievement["current"],
            maximum=aurora_achievement["max"],
            status=aurora_summary["status"],
            description=(
                "Living World Season 3 mastery collections and "
                "Wayfarer's Henge planning."
            ),
        ),
        _goal_card(
            key="vision",
            name="Vision",
            current=vision_achievement["current"],
            maximum=vision_achievement["max"],
            status=(
                "completed"
                if vision_achievement["max"]
                and vision_achievement["current"]
                >= vision_achievement["max"]
                else "in_progress"
            ),
            description=(
                "Vision collections, weapon skins, crafting "
                "requirements, and dependencies."
            ),
        ),
        _goal_card(
            key="regalia",
            name=regalia_progress["name"],
            current=regalia_progress["completed"],
            maximum=regalia_progress["total"],
            status=regalia_status,
            description=(
                "Achievement progress and dependency-aware "
                "completion tracking."
            ),
        ),
    ]

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "page_title": "Dashboard",
            "app_version": "0.1.0",
            "account": account,
            "goals": goals,
        },
    )
