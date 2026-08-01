import json
from pathlib import Path

from app.services.gw2_api import GW2Client


class RegaliaTracker:

    def __init__(self):
        self.client = GW2Client()

        data_file = Path(__file__).parent.parent / "data" / "regalia.json"

        with open(data_file, "r", encoding="utf-8") as file:
            self.required = json.load(file)

    async def progress(self):
        account_achievements = await self.client.get_account_achievements()

        completed_ids = {
            achievement["id"]
            for achievement in account_achievements
            if achievement.get("done", False)
        }

        steps = []

        for achievement in self.required:
            steps.append({
                "id": achievement["id"],
                "name": achievement["name"],
                "completed": achievement["id"] in completed_ids
            })

        completed_count = sum(
            1 for achievement in steps if achievement["completed"]
        )

        total_count = len(steps)

        return {
            "name": "Prismatic Champion's Regalia",
            "completed": completed_count,
            "total": total_count,
            "percent": round(
                completed_count / total_count * 100,
                1
            ) if total_count else 0,
            "steps": steps
        }