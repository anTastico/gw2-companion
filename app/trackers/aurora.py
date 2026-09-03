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

        self.dependency_definitions = {}
        self._index_dependency_definitions(
            self.data
        )

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

    def _index_dependency_definitions(
        self,
        value
    ):
        if isinstance(value, dict):
            definition_id = value.get("definition_id")
            if definition_id:
                if definition_id in self.dependency_definitions:
                    raise ValueError(
                        f"Duplicate Aurora dependency definition: "
                        f"{definition_id!r}"
                    )

                self.dependency_definitions[
                    definition_id
                ] = value

            for child in value.values():
                self._index_dependency_definitions(
                    child
                )

        elif isinstance(value, list):
            for child in value:
                self._index_dependency_definitions(
                    child
                )

    def _get_dependency_definition(
        self,
        dependency_ref: dict | str
    ):
        if isinstance(dependency_ref, str):
            definition_name = dependency_ref
            achievement_id = None
        else:
            definition_name = dependency_ref.get(
                "definition"
            )
            achievement_id = dependency_ref.get(
                "achievement_id"
            )

        dependency = self.dependency_definitions.get(
            definition_name
        )

        if dependency is None:
            raise KeyError(
                f"Unknown Aurora dependency definition: "
                f"{definition_name!r}"
            )

        if achievement_id is None:
            return dependency

        stage = self._find_dependency_stage(
            dependency=dependency,
            achievement_id=achievement_id
        )

        if stage is None:
            raise KeyError(
                f"Aurora dependency definition "
                f"{definition_name!r} does not contain "
                f"achievement {achievement_id}."
            )

        return stage

    def _find_dependency_stage(
        self,
        dependency: dict,
        achievement_id: int
    ):
        if dependency.get("achievement_id") == achievement_id:
            return dependency

        next_dependency = dependency.get(
            "next_dependency"
        )
        if not next_dependency:
            return None

        return self._find_dependency_stage(
            dependency=next_dependency,
            achievement_id=achievement_id
        )

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
            dependency_ref = objective.get("dependency_ref")

            if dependency_ref:
                dependency = self._get_dependency_definition(
                    dependency_ref
                )

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

        if tracking == "achievement_set":
            return self._resolve_achievement_set_dependency(
                dependency=dependency,
                account_progress=account_progress
            )

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
            prerequisites_complete = all(
                prerequisite_bit in completed_bits
                for prerequisite_bit in prerequisites
            )
            available = (
                not completed
                and prerequisites_complete
            )

            objective = dict(definition)
            objective.update({
                "completed": completed,
                "available": available,
                "prerequisites_complete": prerequisites_complete,
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

        if completed:
            available_objectives = []

        resolved = {
            "achievement_id": achievement_id,
            "name": dependency.get("name"),
            "tracking": tracking,
            "current": current,
            "required": required,
            "eligible": len(definitions),
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

        next_dependency = dependency.get("next_dependency")
        if completed and next_dependency:
            next_resolved = self._resolve_achievement_dependency(
                dependency=next_dependency,
                account_progress=account_progress
            )
            next_resolved["previous_dependency"] = {
                "achievement_id": achievement_id,
                "name": dependency.get("name"),
                "completed": True
            }
            next_resolved["dependency_transitioned"] = True
            return next_resolved

        return resolved

    def _resolve_achievement_set_dependency(
        self,
        dependency: dict,
        account_progress: dict
    ):
        achievement_id = dependency["achievement_id"]
        meta_progress = account_progress.get(achievement_id, {})
        definitions = dependency.get("objectives", [])
        required = dependency.get("required", len(definitions))
        resolved_objectives = []

        for definition in definitions:
            child_id = definition["achievement_id"]
            child_progress = account_progress.get(child_id, {})
            completed = child_progress.get("done", False)

            dependency_ref = definition.get(
                "dependency_ref"
            )
            child_dependency = None

            if dependency_ref:
                child_dependency = (
                    self._get_dependency_definition(
                        dependency_ref
                    )
                )

            prerequisite_ids = list(
                definition.get(
                    "prerequisite_achievement_ids",
                    []
                )
            )

            if child_dependency:
                referenced_prerequisite_id = (
                    child_dependency.get(
                        "prerequisite_achievement_id"
                    )
                )
                if (
                    referenced_prerequisite_id is not None
                    and referenced_prerequisite_id
                    not in prerequisite_ids
                ):
                    prerequisite_ids.append(
                        referenced_prerequisite_id
                    )

            missing_prerequisite_ids = [
                prerequisite_id
                for prerequisite_id in prerequisite_ids
                if not account_progress.get(
                    prerequisite_id,
                    {}
                ).get("done", False)
            ]

            prerequisites_complete = (
                len(missing_prerequisite_ids) == 0
            )
            available = (
                not completed
                and prerequisites_complete
            )

            objective = dict(definition)
            objective.update({
                "completed": completed,
                "available": available,
                "prerequisites_complete": prerequisites_complete,
                "missing_prerequisite_achievement_ids": (
                    missing_prerequisite_ids
                )
            })

            if child_dependency:
                objective["dependency"] = (
                    self._resolve_achievement_dependency(
                        dependency=child_dependency,
                        account_progress=account_progress
                    )
                )

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

        direct_current = len(completed_objectives)
        meta_current = meta_progress.get("current", direct_current)
        current = min(
            max(direct_current, meta_current),
            required
        )
        completed = meta_progress.get(
            "done",
            current >= required
        )

        available_objectives = [
            objective
            for objective in missing_objectives
            if objective["available"]
        ]

        available_objectives.sort(
            key=lambda objective: (
                objective.get("priority", 50),
                objective.get("achievement_id", 0)
            )
        )

        if completed:
            available_objectives = []

        resolved = {
            "achievement_id": achievement_id,
            "name": dependency.get("name"),
            "tracking": "achievement_set",
            "current": current,
            "required": required,
            "eligible": len(definitions),
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

        next_dependency = dependency.get("next_dependency")
        if completed and next_dependency:
            next_resolved = self._resolve_achievement_dependency(
                dependency=next_dependency,
                account_progress=account_progress
            )
            next_resolved["previous_dependency"] = {
                "achievement_id": achievement_id,
                "name": dependency.get("name"),
                "completed": True
            }
            next_resolved["dependency_transitioned"] = True
            return next_resolved

        return resolved

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