import httpx

from app.core.config import GW2_API_KEY


class GW2Client:
    BASE_URL = "https://api.guildwars2.com/v2"

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {GW2_API_KEY}"
        }

    async def get(self, endpoint: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}{endpoint}",
                headers=self.headers
            )

            response.raise_for_status()

            return response.json()

    async def get_account(self):
        data = await self.get("/account")

        return {
            "account_name": data["name"],
            "world": data["world"],
            "fractal_level": data["fractal_level"],
            "commander": data["commander"],
            "daily_ap": data["daily_ap"],
            "monthly_ap": data["monthly_ap"],
            "wvw_rank": data["wvw_rank"],
        }

    async def get_account_achievements(self):
        return await self.get("/account/achievements")

    async def get_achievement(self, achievement_id: int):
        return await self.get(f"/achievements/{achievement_id}")

    