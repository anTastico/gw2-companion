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


def _collection_status(collection: dict) -> str:
    if collection.get("completed", False):
        return "complete"

    if collection.get("current", 0) > 0:
        return "active"

    if collection.get("unlocked") is False:
        return "locked"

    if collection.get("actionable") is False:
        return "blocked"

    return "active"


def _objective_view(objective: dict) -> dict:
    dependency = objective.get("dependency") or {}
    next_step = dependency.get("next_step") or {}
    next_objective = dependency.get("next_objective") or {}

    dependency_title = (
        next_step.get("name")
        or next_objective.get("name")
        or dependency.get("name")
    )

    dependency_action = (
        next_step.get("action")
        or next_objective.get("action")
        or dependency.get("action")
    )

    return {
        "name": objective.get("name", "Unnamed objective"),
        "completed": objective.get("completed", False),
        "action": objective.get("action"),
        "location": objective.get("location"),
        "activity": objective.get("activity"),
        "dependency_title": dependency_title,
        "dependency_action": dependency_action,
    }


def _collection_view(collection: dict) -> dict:
    maximum = collection.get("max", 0)
    current = collection.get("current", 0)
    completed = collection.get("completed", False)

    if completed and maximum:
        current = maximum

    progress = _progress(current, maximum)

    if completed:
        raw_missing_objectives = []
    elif collection.get("missing_objectives") is not None:
        raw_missing_objectives = collection.get(
            "missing_objectives",
            [],
        )
    else:
        raw_missing_objectives = (
            collection.get("objective_progress", {})
            .get("missing_objectives", [])
        )

    missing_objectives = [
        _objective_view(objective)
        for objective in raw_missing_objectives
    ]

    return {
        "name": collection.get("name", "Unnamed collection"),
        "status": _collection_status(collection),
        "unlocked": collection.get("unlocked", True),
        "actionable": collection.get("actionable", True),
        "completed": completed,
        "missing_count": len(missing_objectives),
        "missing_objectives": missing_objectives,
        "tracking": collection.get("tracking"),
        "action": collection.get("action"),
        "location": collection.get("location"),
        **progress,
    }


def _crafting_view(crafting: list[dict]) -> list[dict]:
    rows = []

    for item in crafting:
        required = item.get("required", 0)
        owned = item.get("owned", 0)

        rows.append({
            "name": item.get("name", "Unknown item"),
            "owned": owned,
            "required": required,
            "completed": item.get(
                "completed",
                owned >= required if required else False,
            ),
        })

    return rows


@router.get("/app/goal/aurora", name="web_goal_aurora")
async def web_goal_aurora(request: Request):
    account_state = await AccountState.load(client=gw2)
    progress = await aurora.progress(
        account_state=account_state
    )

    stages = []
    for stage in progress.get("stages", []):
        stages.append({
            "name": stage.get("name", "Unnamed stage"),
            "status": stage.get("status", "in_progress"),
            "current": stage.get("current", 0),
            "max": stage.get("max", 0),
            "percent": stage.get("percent", 0),
            "collections": [
                _collection_view(collection)
                for collection in stage.get("collections", [])
            ],
        })

    return templates.TemplateResponse(
        request=request,
        name="goals/aurora.html",
        context={
            "page_title": "Aurora",
            "app_version": "0.1.0",
            "goal_name": progress.get("name", "Aurora"),
            "summary": progress.get("summary", {}),
            "stages": stages,
            "crafting": _crafting_view(
                progress.get("crafting", [])
            ),
        },
    )


@router.get("/app/goal/vision", name="web_goal_vision")
async def web_goal_vision(request: Request):
    account_state = await AccountState.load(client=gw2)
    progress = await vision.progress(
        account_state=account_state
    )

    stages = []
    for stage in progress.get("stages", []):
        stage_complete = _vision_stage_completed(stage)
        stage_current = _vision_stage_current(stage)

        stages.append({
            "name": stage.get("name", "Unnamed stage"),
            "status": (
                "completed"
                if stage_complete
                else "in_progress"
            ),
            "current": stage_current,
            "max": stage.get("max", 0),
            "percent": round(
                stage_current / stage.get("max", 0) * 100,
                1,
            ) if stage.get("max", 0) else 0,
            "collections": [
                _collection_view(collection)
                for collection in stage.get("collections", [])
            ],
        })

    return templates.TemplateResponse(
        request=request,
        name="goals/vision.html",
        context={
            "page_title": "Vision",
            "app_version": "0.1.0",
            "goal_name": progress.get("name", "Vision"),
            "summary": progress.get("summary", {}),
            "stages": stages,
            "current_phase": next(
                (
                    stage["name"]
                    for stage in stages
                    if stage["status"] != "completed"
                ),
                "Collections complete",
            ),
            "crafting": _crafting_view(
                progress.get("crafting", [])
            ),
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
