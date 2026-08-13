import json
from pathlib import Path

from app.services.gw2_api import GW2Client
from app.services.account_inventory import AccountInventory
from app.services.requirements import RequirementAnalyzer


class VisionTracker:

    def __init__(self):
        self.client = GW2Client()
        self.inventory = AccountInventory()
        self.requirements = RequirementAnalyzer()

        data_file = (
            Path(__file__).parent.parent
            / "game_data"
            / "vision.json"
        )

        with open(data_file, "r", encoding="utf-8") as file:
            self.data = json.load(file)

    async def progress(self):
        account_achievements = await self.client.get_account_achievements()

        account_progress = {
            achievement["id"]: achievement
            for achievement in account_achievements
        }

        stages = []

        for stage in self.data["stages"]:
            collections = []

            stage_current = 0
            stage_max = 0

            for collection in stage["collections"]:
                progress = account_progress.get(collection["id"], {})

                completed_bits = progress.get("bits", [])
                current = len(completed_bits)

                max_steps = collection["max"]

                collections.append({
                    "id": collection["id"],
                    "name": collection["name"],
                    "current": current,
                    "max": max_steps,
                    "completed": progress.get("done", False)
                })

                stage_current += current
                stage_max += max_steps

            stages.append({
                "name": stage["name"],
                "current": stage_current,
                "max": stage_max,
                "percent": round(
                    stage_current / stage_max * 100,
                    1
                ) if stage_max else 0,
                "collections": collections
            })

        item_counts = await self.inventory.get_item_counts()

        crafting = []

        for item in self.data["crafting"]:
            owned = item_counts.get(item["id"], 0)
            required = item["required"]

            crafting_item = {
                "id": item["id"],
                "name": item["name"],
                "owned": owned,
                "required": required,
                "completed": owned >= required
            }

            if (
                str(item["id"]) in self.requirements.recipes
                and not crafting_item["completed"]
            ):
                analysis = await self.requirements.analyze_recipe(
                    item_id=item["id"],
                    item_counts=item_counts
                )

                crafting_item["missing_materials"] = (
                    analysis["missing_materials"]
                )

            crafting.append(crafting_item)

        recipe_ids = [
            item["id"]
            for item in self.data["crafting"]
            if str(item["id"]) in self.requirements.recipes
        ]

        missing_materials = await self.requirements.analyze_recipes(
            item_ids=recipe_ids,
            item_counts=item_counts
        )

        achievement_current = sum(
            stage["current"]
            for stage in stages
        )

        achievement_max = sum(
            stage["max"]
            for stage in stages
        )

        summary = {
            "achievement_progress": {
                "current": achievement_current,
                "max": achievement_max,
                "percent": round(
                    achievement_current / achievement_max * 100,
                    1
                ) if achievement_max else 0
            },
            "missing_materials": missing_materials
        }
        return {
            "name": self.data["name"],
            "stages": stages,
            "crafting": crafting,
            "summary": summary
        }