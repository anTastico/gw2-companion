import json
from pathlib import Path

from app.services.gw2_api import GW2Client


class BaseTracker:

    def __init__(self, name: str, data_filename: str):
        self.name = name
        self.client = GW2Client()

        data_file = (
            Path(__file__).parent.parent
            / "game_data"
            / data_filename
        )

        with open(data_file, "r", encoding="utf-8") as file:
            self.required = json.load(file)

    async def progress(self, account_state=None):
        if account_state is not None:
            account_progress = account_state.achievement_by_id
        else:
            account_achievements = (
                await self.client.get_account_achievements()
            )

            account_progress = {
                achievement["id"]: achievement
                for achievement in account_achievements
            }

        steps = []

        for achievement in self.required:
            progress = account_progress.get(achievement["id"], {})

            step = {
                "id": achievement["id"],
                "name": achievement["name"],
                "completed": progress.get("done", False),
                "current": progress.get("current", 0),
                "max": progress.get("max", 1)
            }

            steps.append(step)

        completed_count = sum(
            1 for step in steps if step["completed"]
        )

        total_count = len(steps)

        return {
            "name": self.name,
            "completed": completed_count,
            "total": total_count,
            "percent": round(
                completed_count / total_count * 100,
                1
            ) if total_count else 0,
            "steps": steps
        }