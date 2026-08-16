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
        completed_stage_names = set()

        for stage in self.data["stages"]:
            collections = []

            stage_current = 0
            stage_max = 0

            for collection in stage["collections"]:
                progress = account_progress.get(
                    collection["id"],
                    {}
                )

                tracking = collection.get(
                    "tracking",
                    "bits"
                )

                max_steps = collection["max"]

                if tracking == "count_only":
                    current = min(
                        progress.get(
                            "current",
                            0
                        ),
                        max_steps
                    )
                else:
                    completed_bits = progress.get(
                        "bits",
                        []
                    )

                    current = len(
                        completed_bits
                    )

                completed = progress.get(
                    "done",
                    current >= max_steps
                )

                collection_result = {
                    "id": collection["id"],
                    "name": collection["name"],
                    "current": current,
                    "max": max_steps,
                    "completed": completed
                }

                if tracking == "count_only":
                    prerequisite = collection.get(
                        "prerequisite"
                    )

                    prerequisite_met = self._prerequisite_met(
                        prerequisite=prerequisite,
                        completed_stage_names=completed_stage_names
                    )

                    if prerequisite is not None:
                        unlocked = prerequisite_met
                    elif progress:
                        unlocked = progress.get(
                            "unlocked",
                            True
                        )
                    else:
                        unlocked = False

                    collection_result.update({
                        "tracking": tracking,
                        "unlocked": unlocked,
                        "activity": collection.get(
                            "activity"
                        ),
                        "minimum_minutes": collection.get(
                            "minimum_minutes"
                        ),
                        "ideal_minutes": collection.get(
                            "ideal_minutes"
                        ),
                        "action": collection.get(
                            "action"
                        )
                    })

                    if prerequisite is not None:
                        collection_result[
                            "prerequisite"
                        ] = prerequisite

                        collection_result[
                            "prerequisite_met"
                        ] = prerequisite_met

                objective_data = collection.get(
                    "objectives"
                )

                if objective_data:
                    completed_bits = progress.get(
                        "bits",
                        []
                    )

                    objectives = []

                    for objective in objective_data:
                        bit = objective["bit"]

                        objective_result = {
                            "bit": bit,
                            "name": objective["name"],
                            "completed": (
                                bit in completed_bits
                            ),
                            "activity": objective.get(
                                "activity"
                            ),
                            "location": objective.get(
                                "location"
                            ),
                            "minimum_minutes": objective.get(
                                "minimum_minutes"
                            ),
                            "ideal_minutes": objective.get(
                                "ideal_minutes"
                            ),
                            "action": objective.get(
                                "action"
                            )
                        }

                        dependency = objective.get(
                            "dependency"
                        )

                        if dependency:
                            objective_result[
                                "dependency"
                            ] = self._resolve_dependency(
                                dependency=dependency,
                                account_progress=account_progress
                            )

                        objectives.append(
                            objective_result
                        )

                    collection_result[
                        "objectives"
                    ] = objectives

                    collection_result[
                        "completed_objectives"
                    ] = [
                        objective
                        for objective in objectives
                        if objective["completed"]
                    ]

                    collection_result[
                        "missing_objectives"
                    ] = [
                        objective
                        for objective in objectives
                        if not objective["completed"]
                    ]

                collections.append(
                    collection_result
                )

                stage_current += current
                stage_max += max_steps

            if (
                stage_max > 0
                and stage_current >= stage_max
            ):
                completed_stage_names.add(
                    stage["name"]
                )

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
            owned = item_counts.get(
                item["id"],
                0
            )

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

            crafting.append(
                crafting_item
            )

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
                    achievement_current
                    / achievement_max
                    * 100,
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

    def _resolve_dependency(
        self,
        dependency: dict,
        account_progress: dict
    ):
        achievement_id = dependency.get(
            "achievement_id"
        )

        tracking = dependency.get(
            "tracking"
        )

        progress = account_progress.get(
            achievement_id,
            {}
        )

        dependency_result = {
            "achievement_id": achievement_id,
            "name": dependency.get(
                "name"
            ),
            "tracking": tracking
        }

        if tracking == "achievement_bits":
            completed_bits = progress.get(
                "bits",
                []
            )

            required = dependency.get(
                "required",
                len(
                    dependency.get(
                        "objectives",
                        []
                    )
                )
            )

            current = min(
                progress.get(
                    "current",
                    len(completed_bits)
                ),
                required
            )

            completed = progress.get(
                "done",
                current >= required
            )

            dependency_objectives = []

            for objective in dependency.get(
                "objectives",
                []
            ):
                bit = objective["bit"]

                dependency_objective = {
                    "bit": bit,
                    "name": objective["name"],
                    "completed": (
                        bit in completed_bits
                    )
                }

                for field in (
                    "activity",
                    "location",
                    "minimum_minutes",
                    "ideal_minutes",
                    "action",
                    "bundle",
                    "focus_type"
                ):
                    if field in objective:
                        dependency_objective[field] = (
                            objective[field]
                        )

                dependency_objectives.append(
                    dependency_objective
                )

            dependency_result.update({
                "current": current,
                "required": required,
                "percent": round(
                    current / required * 100,
                    1
                ) if required else 0,
                "completed": completed,
                "objectives": dependency_objectives,
                "completed_objectives": [
                    objective
                    for objective in dependency_objectives
                    if objective["completed"]
                ],
                "missing_objectives": [
                    objective
                    for objective in dependency_objectives
                    if not objective["completed"]
                ]
            })

        alternative = dependency.get(
            "alternative"
        )

        if alternative:
            dependency_result[
                "alternative"
            ] = alternative

        return dependency_result

    def _prerequisite_met(
        self,
        prerequisite: dict | None,
        completed_stage_names: set
    ):
        if prerequisite is None:
            return True

        prerequisite_type = prerequisite.get(
            "type"
        )

        if prerequisite_type == "stage":
            return (
                prerequisite.get("name")
                in completed_stage_names
            )

        return False