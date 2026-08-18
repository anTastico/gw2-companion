import asyncio
import httpx

from app.core.config import GW2_API_KEY


class GW2Client:
    BASE_URL = "https://api.guildwars2.com/v2"

    def __init__(self, http_client=None):
        self.headers = {
            "Authorization": f"Bearer {GW2_API_KEY}"
        }
        self.http_client = http_client

    async def get(self, endpoint: str):
        timeout = httpx.Timeout(20.0)

        for attempt in range(3):
            try:
                if self.http_client is not None:
                    response = await self.http_client.get(
                        f"{self.BASE_URL}{endpoint}",
                        headers=self.headers
                    )
                else:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        response = await client.get(
                            f"{self.BASE_URL}{endpoint}",
                            headers=self.headers
                        )

                response.raise_for_status()

                return response.json()

            except httpx.ReadTimeout:
                if attempt == 2:
                    raise

                await asyncio.sleep(1)

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

    async def get_bank(self):
        return await self.get("/account/bank")

    async def get_materials(self):
        return await self.get("/account/materials")

    async def get_shared_inventory(self):
        return await self.get("/account/inventory")

    async def get_characters(self):
        return await self.get("/characters?page=0&page_size=200")