from typing import Literal

from fastapi import FastAPI, Query

from app.services.gw2_api import GW2Client
from app.services.account_inventory import AccountInventory
from app.services.requirements import RequirementAnalyzer
from app.services.recommendations import RecommendationService
from app.services.session_planner import SessionPlanner
from app.trackers.regalia import RegaliaTracker
from app.trackers.vision import VisionTracker
from app.trackers.aurora import AuroraTracker


gw2 = GW2Client()

regalia = RegaliaTracker()
vision = VisionTracker()
aurora = AuroraTracker()

inventory = AccountInventory()
requirements = RequirementAnalyzer()
recommendations = RecommendationService()
session_planner = SessionPlanner()


app = FastAPI(
    title="GW2 Companion",
    description="A self-hosted Guild Wars 2 companion.",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "application": "GW2 Companion",
        "version": "0.1.0",
        "status": "Running"
    }


@app.get("/account")
async def account():
    return await gw2.get_account()


@app.get("/achievements")
async def achievements():
    return await gw2.get_account_achievements()


@app.get("/achievement/{achievement_id}")
async def achievement(achievement_id: int):
    return await gw2.get_achievement(achievement_id)


@app.get("/tracker/regalia")
async def regalia_progress():
    return await regalia.progress()


@app.get("/tracker/vision")
async def vision_progress():
    return await vision.progress()


@app.get("/tracker/aurora")
async def aurora_progress():
    return await aurora.progress()


@app.get("/inventory/item/{item_id}")
async def item_count(item_id: int):
    count = await inventory.get_item_count(
        item_id
    )

    return {
        "item_id": item_id,
        "count": count
    }


@app.get("/requirements/{item_id}")
async def item_requirements(
    item_id: int
):
    return await requirements.analyze_recipe(
        item_id
    )


@app.get("/recommendations")
async def get_recommendations(
    mode: Literal[
        "progress",
        "quick",
        "play"
    ] = Query(
        default="progress"
    ),
    goal: Literal[
        "vision",
        "aurora",
        "regalia"
    ] | None = Query(
        default=None
    ),
    activity: Literal[
        "achievement",
        "open_world",
        "fractals",
        "wvw",
        "vendor",
        "trading_post",
        "acquisition"
    ] | None = Query(
        default=None
    ),
    minutes: int | None = Query(
        default=None,
        ge=5,
        le=360
    )
):
    return await recommendations.get_recommendations(
        mode=mode,
        goal=goal,
        activity=activity,
        minutes=minutes
    )


@app.get("/session-plan")
async def get_session_plan(
    minutes: int = Query(
        ge=5,
        le=360
    ),
    goal: Literal[
        "vision",
        "aurora",
        "regalia"
    ] | None = Query(
        default=None
    ),
    activity: Literal[
        "achievement",
        "open_world",
        "fractals",
        "wvw",
        "vendor",
        "trading_post",
        "acquisition"
    ] | None = Query(
        default=None
    )
):
    return await session_planner.build_plan(
        minutes=minutes,
        goal=goal,
        activity=activity
    )