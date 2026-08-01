from app.services.gw2_api import GW2Client

from fastapi import FastAPI

gw2 = GW2Client()

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