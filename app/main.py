from fastapi import FastAPI

from app.services.gw2_api import GW2Client
from app.trackers.regalia import RegaliaTracker
from app.trackers.vision import VisionTracker
from app.services.account_inventory import AccountInventory
from app.services.requirements import RequirementAnalyzer

gw2 = GW2Client()
regalia = RegaliaTracker()
vision = VisionTracker()
inventory = AccountInventory()
requirements = RequirementAnalyzer()


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

@app.get("/inventory/item/{item_id}")
async def item_count(item_id: int):
    count = await inventory.get_item_count(item_id)

    return {
        "item_id": item_id,
        "count": count
    }
@app.get("/requirements/{item_id}")
async def item_requirements(item_id: int):
    return await requirements.analyze_recipe(item_id)