from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.templating import Jinja2Templates

from app.services.account_state import AccountState
from app.services.recommendations import RecommendationService
from app.services.session_planner import SessionPlanner
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
recommendations = RecommendationService()
session_planner = SessionPlanner()


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
    focus_label: str | None = None,
    overall_current: int | None = None,
    overall_maximum: int | None = None,
) -> dict:
    progress = _progress(current, maximum)

    badge_class = ""
    badge_label = "Tracked"

    if status == "completed":
        badge_class = "badge-complete"
        badge_label = "Complete"
    elif status == "ready_to_craft":
        badge_class = "badge-active"
        badge_label = "Ready to craft"
    elif status == "in_progress":
        badge_class = "badge-active"
        badge_label = "Active"
    elif status == "locked":
        badge_label = "Locked"

    overall = None
    if overall_current is not None and overall_maximum is not None:
        overall = _progress(overall_current, overall_maximum)

    return {
        "key": key,
        "name": name,
        "status": status,
        "badge_label": badge_label,
        "badge_class": badge_class,
        "description": description,
        "focus_label": focus_label,
        "overall": overall,
        **progress,
    }


def _current_aurora_stage(stages: list[dict]) -> dict | None:
    for stage in stages:
        if stage.get("status") != "completed":
            return stage
    return stages[-1] if stages else None


def _vision_stage_completed(stage: dict) -> bool:
    collections = stage.get("collections", [])

    return bool(collections) and all(
        collection.get("completed", False)
        for collection in collections
    )


def _vision_stage_current(stage: dict) -> int:
    if _vision_stage_completed(stage):
        return stage.get("max", 0)

    return stage.get("current", 0)


def _current_vision_stage(stages: list[dict]) -> dict | None:
    for stage in stages:
        if not _vision_stage_completed(stage):
            return stage

    return stages[-1] if stages else None


def _vision_overall_progress(stages: list[dict]) -> dict:
    current = sum(
        _vision_stage_current(stage)
        for stage in stages
    )
    maximum = sum(
        stage.get("max", 0)
        for stage in stages
    )

    return _progress(current, maximum)


def _all_crafting_complete(crafting: list[dict]) -> bool:
    return bool(crafting) and all(
        item.get("completed", False)
        for item in crafting
    )


DAILY_PRIORITY_LABELS = {
    "hard_gate": "Hard daily gate",
    "limited_attempt": "Limited daily attempt",
    "soft_cap": "Daily soft cap",
    "optional": "Optional daily route",
}


def _daily_priority_view(recommendation: dict) -> dict:
    opportunity_type = recommendation.get(
        "daily_opportunity_type",
        "daily",
    )

    details = []

    label = DAILY_PRIORITY_LABELS.get(
        opportunity_type,
        "Daily opportunity",
    )
    details.append(label)

    location = recommendation.get("location")
    if location:
        details.append(location)

    progress = recommendation.get("progress")
    if progress:
        details.append(progress)

    return {
        "title": recommendation.get(
            "title",
            "Daily opportunity",
        ),
        "goal": recommendation.get("goal"),
        "type": opportunity_type,
        "details": " · ".join(details),
        "action": recommendation.get("action"),
        "score": recommendation.get("score"),
    }


def _select_daily_priorities(
    recommendations_result: dict,
    limit: int = 3,
) -> list[dict]:
    daily = [
        recommendation
        for recommendation in recommendations_result.get(
            "recommendations",
            [],
        )
        if recommendation.get("daily_opportunity_type")
    ]

    priority_order = {
        "hard_gate": 0,
        "limited_attempt": 1,
        "soft_cap": 2,
        "optional": 3,
    }

    daily.sort(
        key=lambda recommendation: (
            priority_order.get(
                recommendation.get("daily_opportunity_type"),
                99,
            ),
            -recommendation.get("score", 0),
        )
    )

    return [
        _daily_priority_view(recommendation)
        for recommendation in daily[:limit]
    ]


def _plan_step_view(step: dict) -> dict:
    return {
        "order": step.get("order"),
        "title": step.get("title", "Untitled step"),
        "goal": step.get("goal"),
        "location": step.get("location"),
        "allocated_minutes": step.get("allocated_minutes", 0),
        "action": step.get("action"),
        "reason": step.get("reason"),
        "time_gated": step.get("time_gated", False),
    }


@router.get("/app/session-plan", name="web_session_plan")
async def web_session_plan(
    request: Request,
    minutes: int = Query(ge=5, le=360),
):
    plan = await session_planner.build_plan(
        minutes=minutes
    )

    return templates.TemplateResponse(
        request=request,
        name="partials/session_plan.html",
        context={
            "plan": plan,
            "steps": [
                _plan_step_view(step)
                for step in plan.get("steps", [])
            ],
        },
    )


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

    recommendations_result = await recommendations.get_recommendations(
        mode="progress",
        full_candidate_pool=True,
        account_state=account_state,
    )
    daily_priorities = _select_daily_priorities(
        recommendations_result
    )

    aurora_summary = aurora_progress["summary"]
    aurora_achievement = aurora_summary["achievement_progress"]
    aurora_stage = _current_aurora_stage(
        aurora_progress["stages"]
    )

    vision_summary = vision_progress["summary"]
    vision_achievement = vision_summary["achievement_progress"]
    vision_stage = _current_vision_stage(
        vision_progress["stages"]
    )
    vision_overall = _vision_overall_progress(
        vision_progress["stages"]
    )

    regalia_status = (
        "completed"
        if regalia_progress["completed"] >= regalia_progress["total"]
        else "in_progress"
    )

    aurora_collections_complete = all(
        stage.get("status") == "completed"
        for stage in aurora_progress["stages"]
    )
    aurora_crafting_complete = _all_crafting_complete(
        aurora_progress["crafting"]
    )

    if aurora_collections_complete:
        aurora_card_status = (
            "completed"
            if aurora_crafting_complete
            else "ready_to_craft"
        )
        aurora_focus_label = "Collections complete"
        aurora_current = aurora_achievement["max"]
        aurora_maximum = aurora_achievement["max"]
    else:
        aurora_card_status = aurora_summary["status"]
        aurora_focus_label = (
            aurora_stage["name"]
            if aurora_stage
            else "Current stage"
        )
        aurora_current = (
            aurora_stage["current"]
            if aurora_stage
            else aurora_achievement["current"]
        )
        aurora_maximum = (
            aurora_stage["max"]
            if aurora_stage
            else aurora_achievement["max"]
        )

    vision_collections_complete = all(
        _vision_stage_completed(stage)
        for stage in vision_progress["stages"]
    )
    vision_crafting_complete = _all_crafting_complete(
        vision_progress["crafting"]
    )

    if vision_collections_complete:
        vision_card_status = (
            "completed"
            if vision_crafting_complete
            else "ready_to_craft"
        )
        vision_focus_label = "Collections complete"
        vision_current = vision_achievement["max"]
        vision_maximum = vision_achievement["max"]
    else:
        vision_card_status = "in_progress"
        vision_focus_label = (
            vision_stage["name"]
            if vision_stage
            else "Current stage"
        )
        vision_current = (
            _vision_stage_current(vision_stage)
            if vision_stage
            else vision_overall["current"]
        )
        vision_maximum = (
            vision_stage["max"]
            if vision_stage
            else vision_achievement["max"]
        )

    goals = [
        _goal_card(
            key="aurora",
            name="Aurora",
            current=aurora_current,
            maximum=aurora_maximum,
            status=aurora_card_status,
            focus_label=aurora_focus_label,
            overall_current=aurora_achievement["current"],
            overall_maximum=aurora_achievement["max"],
            description=(
                "Living World Season 3 mastery collections and "
                "Wayfarer's Henge planning."
            ),
        ),
        _goal_card(
            key="vision",
            name="Vision",
            current=vision_current,
            maximum=vision_maximum,
            status=vision_card_status,
            focus_label=vision_focus_label,
            overall_current=vision_overall["current"],
            overall_maximum=vision_overall["max"],
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
            focus_label="Required achievements",
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
            "daily_priorities": daily_priorities,
        },
    )
