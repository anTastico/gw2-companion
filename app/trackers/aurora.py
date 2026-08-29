import json
from pathlib import Path

from app.services.gw2_api import GW2Client
from app.services.account_inventory import AccountInventory
from app.services.requirements import RequirementAnalyzer


class AuroraTracker:

    def __init__(self):
        self.client = GW2Client()
        self.inventory = AccountInventory()
        self.requirements = RequirementAnalyzer()

        data_file = (
            Path(__file__).parent.parent
            / "game_data"
            / "aurora.json"
        )

        with open(data_file, "r", encoding="utf-8") as file:
            self.data = json.load(file)

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

        item_counts = (
            account_state.item_counts
            if account_state is not None
            else await self.inventory.get_item_counts()
        )
        stages = []

        for stage in self.data["stages"]:
            collections = []
            stage_current = 0
            stage_max = 0
            stage_achievement_id = stage.get("achievement_id")

            if (
                stage_achievement_id is None
                and len(stage["collections"]) == 1
            ):
                stage_achievement_id = stage["collections"][0]["id"]

            stage_unlocked = (
                stage_achievement_id in account_progress
                if stage_achievement_id is not None
                else True
            )

            unlock = None

            if not stage_unlocked and stage.get("unlock"):
                unlock = self._resolve_unlock(
                    unlock_data=stage["unlock"],
                    account_progress=account_progress,
                    item_counts=item_counts
                )

            for collection in stage["collections"]:
                progress = account_progress.get(collection["id"], {})
                completed_bits = progress.get("bits", [])
                current = len(completed_bits)
                max_steps = collection["max"]

                collection_result = {
                    "id": collection["id"],
                    "name": collection["name"],
                    "current": current,
                    "max": max_steps,
                    "completed": progress.get("done", False),
                    "unlocked": stage_unlocked,
                    "actionable": (
                        stage_unlocked
                        and not progress.get("done", False)
                    ),
                    "location": collection.get("location")
                }

                objective_tracking = collection.get(
                    "objective_tracking"
                )

                if (
                    objective_tracking
                    and objective_tracking.get("type")
                    == "achievement_bits"
                ):
                    objective_progress = self._resolve_achievement_bits(
                        objective_tracking=objective_tracking,
                        achievement_progress=progress,
                        account_progress=account_progress
                    )
                    collection_result["objective_progress"] = (
                        objective_progress
                    )
                    current = objective_progress["current"]
                    collection_result["current"] = current

                collections.append(collection_result)

                stage_current += current
                stage_max += max_steps

            stage_completed = (
                stage_unlocked
                and all(
                    collection["completed"]
                    for collection in collections
                )
            )

            if stage_completed:
                status = "completed"
            elif stage_unlocked:
                status = "in_progress"
            else:
                status = "locked"

            stage_result = {
                "name": stage["name"],
                "status": status,
                "current": stage_current,
                "max": stage_max,
                "percent": round(
                    stage_current / stage_max * 100,
                    1
                ) if stage_max else 0,
                "collections": collections
            }

            if unlock is not None:
                stage_result["unlock"] = unlock

            stages.append(stage_result)

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
                crafting_item["missing_materials"] = analysis["missing_materials"]

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

        achievement_current = sum(stage["current"] for stage in stages)
        achievement_max = sum(stage["max"] for stage in stages)

        if all(stage["status"] == "completed" for stage in stages):
            tracker_status = "completed"
        elif any(stage["status"] == "in_progress" for stage in stages):
            tracker_status = "in_progress"
        elif all(stage["status"] == "locked" for stage in stages):
            tracker_status = "locked"
        else:
            tracker_status = "in_progress"

        next_step = None

        for stage in stages:
            if stage["status"] == "completed":
                continue

            next_step = {
                "stage": stage["name"],
                "reason": stage["status"]
            }

            if stage.get("unlock"):
                next_step["unlock"] = stage["unlock"]

            break

        summary = {
            "status": tracker_status,
            "achievement_progress": {
                "current": achievement_current,
                "max": achievement_max,
                "percent": round(
                    achievement_current / achievement_max * 100,
                    1
                ) if achievement_max else 0
            },
            "next_step": next_step,
            "missing_materials": missing_materials
        }

        return {
            "name": self.data["name"],
            "stages": stages,
            "crafting": crafting,
            "summary": summary
        }

    def _resolve_achievement_bits(
        self,
        objective_tracking: dict,
        achievement_progress: dict,
        account_progress: dict | None = None
    ):
        completed_bits = set(
            achievement_progress.get("bits", [])
        )
        objectives = objective_tracking.get("objectives", [])
        resolved_objectives = []

        for objective in objectives:
            resolved = dict(objective)
            bit = objective.get("bit")
            resolved["completed"] = bit in completed_bits

            dependency = objective.get("dependency")
            if dependency and account_progress is not None:
                resolved["dependency"] = (
                    self._resolve_achievement_dependency(
                        dependency=dependency,
                        account_progress=account_progress
                    )
                )

            resolved_objectives.append(resolved)

        missing_objectives = [
            objective
            for objective in resolved_objectives
            if not objective["completed"]
        ]

        group_by = objective_tracking.get("group_by")
        groups = {}

        if group_by:
            for objective in missing_objectives:
                group_name = objective.get(group_by, "Other")
                groups.setdefault(group_name, []).append(objective)

        current = len(resolved_objectives) - len(missing_objectives)

        return {
            "current": current,
            "required": len(resolved_objectives),
            "percent": round(
                current / len(resolved_objectives) * 100,
                1
            ) if resolved_objectives else 0,
            "completed_bits": sorted(completed_bits),
            "missing_count": len(missing_objectives),
            "objectives": resolved_objectives,
            "missing_objectives": missing_objectives,
            "missing_groups": [
                {
                    "name": group_name,
                    "missing_count": len(group_objectives),
                    "objectives": group_objectives
                }
                for group_name, group_objectives in groups.items()
            ]
        }

    def _resolve_achievement_dependency(
        self,
        dependency: dict,
        account_progress: dict
    ):
        tracking = dependency.get("tracking")

        if tracking != "achievement_bits":
            return {
                "achievement_id": dependency.get("achievement_id"),
                "name": dependency.get("name"),
                "tracking": tracking,
                "supported": False
            }

        achievement_id = dependency["achievement_id"]
        progress = account_progress.get(achievement_id, {})
        completed_bits = set(progress.get("bits", []))
        definitions = dependency.get("objectives", [])
        required = dependency.get("required", len(definitions))
        resolved_objectives = []

        for definition in definitions:
            bit = definition["bit"]
            prerequisites = definition.get("prerequisite_bits", [])
            completed = bit in completed_bits
            available = (
                completed
                or all(
                    prerequisite_bit in completed_bits
                    for prerequisite_bit in prerequisites
                )
            )

            objective = dict(definition)
            objective.update({
                "completed": completed,
                "available": available,
                "prerequisites_complete": available,
                "missing_prerequisite_bits": [
                    prerequisite_bit
                    for prerequisite_bit in prerequisites
                    if prerequisite_bit not in completed_bits
                ]
            })
            resolved_objectives.append(objective)

        completed_objectives = [
            objective
            for objective in resolved_objectives
            if objective["completed"]
        ]
        missing_objectives = [
            objective
            for objective in resolved_objectives
            if not objective["completed"]
        ]
        available_objectives = [
            objective
            for objective in missing_objectives
            if objective["available"]
        ]

        available_objectives.sort(
            key=lambda objective: (
                objective.get("priority", 50),
                objective["bit"]
            )
        )

        current = min(
            progress.get("current", len(completed_objectives)),
            required
        )
        completed = progress.get("done", current >= required)

        return {
            "achievement_id": achievement_id,
            "name": dependency.get("name"),
            "tracking": tracking,
            "current": current,
            "required": required,
            "percent": round(
                current / required * 100,
                1
            ) if required else 0,
            "completed": completed,
            "objectives": resolved_objectives,
            "completed_objectives": completed_objectives,
            "missing_objectives": missing_objectives,
            "available_objectives": available_objectives,
            "available": len(available_objectives),
            "next_objective": (
                available_objectives[0]
                if available_objectives
                else None
            )
        }

    def _resolve_unlock(
        self,
        unlock_data: dict,
        account_progress: dict,
        item_counts: dict
    ):
        requirements = []

        for requirement in unlock_data.get("requirements", []):
            achievement_id = requirement["achievement_id"]
            achievement_progress = account_progress.get(
                achievement_id,
                {}
            )
            reward_item_id = requirement.get("reward_item_id")

            reward_owned = (
                item_counts.get(reward_item_id, 0) > 0
                if reward_item_id is not None
                else False
            )

            completed = (
                achievement_progress.get("done", False)
                or reward_owned
            )

            requirement_result = {
                "achievement_id": achievement_id,
                "name": requirement["name"],
                "completed": completed,
                "reward_item_id": reward_item_id,
                "reward_item_name": requirement.get("reward_item_name"),
                "reward_owned": reward_owned,
                "activity": requirement.get("activity"),
                "location": requirement.get("location"),
                "minimum_minutes": requirement.get("minimum_minutes"),
                "ideal_minutes": requirement.get("ideal_minutes"),
                "action": requirement.get("action")
            }

            objective_tracking = requirement.get("objective_tracking")

            if (
                objective_tracking
                and objective_tracking.get("type") == "achievement_bits"
                and not completed
            ):
                requirement_result["objective_progress"] = (
                    self._resolve_achievement_bits(
                        objective_tracking=objective_tracking,
                        achievement_progress=achievement_progress,
                        account_progress=account_progress
                    )
                )

            requirements.append(requirement_result)

        completed_count = sum(
            1 for requirement in requirements
            if requirement["completed"]
        )
        missing_requirements = [
            requirement
            for requirement in requirements
            if not requirement["completed"]
        ]

        target_item_id = unlock_data.get("item_id")
        target_owned = (
            item_counts.get(target_item_id, 0) > 0
            if target_item_id is not None
            else False
        )

        return {
            "type": unlock_data.get("type"),
            "name": unlock_data["name"],
            "item_id": target_item_id,
            "target_owned": target_owned,
            "current": completed_count,
            "required": len(requirements),
            "percent": round(
                completed_count / len(requirements) * 100,
                1
            ) if requirements else 0,
            "completed": target_owned,
            "action": unlock_data.get("action"),
            "requirements": requirements,
            "completed_requirements": [
                requirement
                for requirement in requirements
                if requirement["completed"]
            ],
            "missing_requirements": missing_requirements,
            "combine": unlock_data.get("combine"),
            "purchase": unlock_data.get("purchase")
        }