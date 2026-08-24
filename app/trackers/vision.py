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

        if account_state is not None:
            item_counts = account_state.item_counts
            recipe_ids = account_state.recipe_ids
        else:
            item_counts = await self.inventory.get_item_counts()
            recipe_ids = set(
                await self.client.get_account_recipes()
            )

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
                            ),
                            "availability_type": objective.get(
                                "availability_type"
                            ),
                            "event_dependent": objective.get(
                                "event_dependent",
                                False
                            ),
                            "group_recommended": objective.get(
                                "group_recommended",
                                False
                            ),
                            "schedule_dependent": objective.get(
                                "schedule_dependent",
                                False
                            ),
                            "playability_note": objective.get(
                                "playability_note"
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
                                account_progress=account_progress,
                                item_counts=item_counts,
                                recipe_ids=recipe_ids
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
        account_progress: dict,
        item_counts: dict,
        recipe_ids: set
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

        if tracking == "achievement":
            required = dependency.get("required", 1)
            current = min(progress.get("current", 0), required)
            completed = progress.get("done", current >= required)
            dependency_result.update({
                "current": current,
                "required": required,
                "percent": round(current / required * 100, 1) if required else 0,
                "completed": completed,
                "objectives": [],
                "completed_objectives": [],
                "missing_objectives": []
            })

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

            if dependency.get("completion_mode") == "threshold":
                completed = current >= required
            else:
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

                objective_achievement_id = objective.get(
                    "achievement_id"
                )

                if objective_achievement_id is not None:
                    objective_progress = account_progress.get(
                        objective_achievement_id,
                        {}
                    )
                    dependency_objective.update({
                        "achievement_id": objective_achievement_id,
                        "current": objective_progress.get(
                            "current",
                            0
                        ),
                        "required": objective_progress.get(
                            "max"
                        )
                    })

                for field in (
                    "activity",
                    "location",
                    "minimum_minutes",
                    "ideal_minutes",
                    "action",
                    "bundle",
                    "focus_type",
                    "event_dependent",
                    "skin_id"
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

        if tracking == "achievement_set":
            definitions = dependency.get("objectives", [])
            required = dependency.get("required", len(definitions))
            dependency_objectives = []

            for objective in definitions:
                objective_id = objective["achievement_id"]
                objective_progress = account_progress.get(
                    objective_id,
                    {}
                )
                objective_current = objective_progress.get(
                    "current",
                    0
                )
                objective_max = objective_progress.get("max")
                objective_done = objective_progress.get("done")

                if objective_done is None:
                    objective_done = bool(
                        objective_max
                        and objective_current >= objective_max
                    )

                dependency_objective = {
                    "achievement_id": objective_id,
                    "name": objective["name"],
                    "completed": bool(objective_done),
                    "current": objective_current,
                    "required": objective_max
                }

                for field in (
                    "activity",
                    "location",
                    "minimum_minutes",
                    "ideal_minutes",
                    "action",
                    "event_dependent",
                    "bundle",
                    "focus_type",
                    "reward"
                ):
                    if field in objective:
                        dependency_objective[field] = objective[field]

                dependency_objectives.append(
                    dependency_objective
                )

            completed_objectives = [
                objective
                for objective in dependency_objectives
                if objective["completed"]
            ]
            missing_objectives = [
                objective
                for objective in dependency_objectives
                if not objective["completed"]
            ]
            current = min(
                len(completed_objectives),
                required
            )

            dependency_result.update({
                "current": current,
                "required": required,
                "percent": round(
                    current / required * 100,
                    1
                ) if required else 0,
                "completed": current >= required,
                "objectives": dependency_objectives,
                "completed_objectives": completed_objectives,
                "missing_objectives": missing_objectives
            })

        if tracking == "achievement_options":
            required = dependency.get("required", 1)
            current = min(progress.get("current", 0), required)
            completed = progress.get("done", current >= required)
            remaining_required = max(required - current, 0)
            options = []

            for option in dependency.get("options", []):
                option_id = option["achievement_id"]
                option_progress = account_progress.get(option_id, {})
                option_done = option_progress.get("done", False)

                prerequisite_achievement_ids = option.get(
                    "prerequisite_achievement_ids",
                    []
                )
                option_available = all(
                    account_progress.get(
                        prerequisite_id,
                        {}
                    ).get("done", False)
                    for prerequisite_id
                    in prerequisite_achievement_ids
                )

                option_result = {
                    "achievement_id": option_id,
                    "name": option["name"],
                    "completed": option_done,
                    "current": option_progress.get("current", 0),
                    "required": option_progress.get("max"),
                    "bits": option_progress.get("bits", []),
                    "priority": option.get("priority", 50),
                    "available": option_available,
                    "prerequisite_achievement_ids": prerequisite_achievement_ids
                }

                for field in (
                    "activity",
                    "location",
                    "minimum_minutes",
                    "ideal_minutes",
                    "action",
                    "event_dependent",
                    "related_objectives",
                    "availability_type",
                    "repeat_required",
                    "group_recommended",
                    "schedule_dependent",
                    "playability_note"
                ):
                    if field in option:
                        option_result[field] = option[field]

                completion_effects = []

                for effect in option.get(
                    "completion_effects",
                    []
                ):
                    target_progress = account_progress.get(
                        effect["achievement_id"],
                        {}
                    )

                    effect_active = True

                    if effect.get("effect") == "complete_bit":
                        target_bit = effect.get("bit")
                        effect_active = (
                            not target_progress.get("done", False)
                            and target_bit not in target_progress.get(
                                "bits",
                                []
                            )
                        )
                    elif effect.get("effect") == "complete_achievement":
                        effect_active = not target_progress.get(
                            "done",
                            False
                        )

                    target_current = target_progress.get(
                        "current",
                        0
                    )
                    target_required = target_progress.get(
                        "max"
                    )

                    completes_achievement = False

                    if effect.get("effect") == "complete_achievement":
                        completes_achievement = effect_active
                    elif (
                        effect.get("effect") == "complete_bit"
                        and effect_active
                        and target_required
                    ):
                        completes_achievement = (
                            target_current + 1
                            >= target_required
                        )

                    same_dependency_ids = {
                        candidate.get("achievement_id")
                        for candidate in dependency.get(
                            "options",
                            []
                        )
                    }

                    effect_result = dict(effect)
                    effect_result["active"] = effect_active
                    effect_result["current"] = target_current
                    effect_result["required"] = target_required
                    effect_result["completes_achievement"] = (
                        completes_achievement
                    )
                    effect_result[
                        "counts_toward_same_dependency"
                    ] = (
                        effect.get("achievement_id")
                        in same_dependency_ids
                    )

                    completion_effects.append(effect_result)

                if completion_effects:
                    option_result["completion_effects"] = (
                        completion_effects
                    )
                    option_result[
                        "active_completion_effects"
                    ] = [
                        effect
                        for effect in completion_effects
                        if effect["active"]
                    ]

                subresults = []
                for subobjective in option.get("objectives", []):
                    bit = subobjective["bit"]
                    sub = {
                        "bit": bit,
                        "name": subobjective["name"],
                        "completed": bit in option_result["bits"]
                    }
                    if "action" in subobjective:
                        sub["action"] = subobjective["action"]
                    subresults.append(sub)

                if subresults:
                    option_result["objectives"] = subresults
                    option_result["missing_objectives"] = [x for x in subresults if not x["completed"]]

                options.append(option_result)

            options.sort(key=lambda x: (
                x["completed"],
                x.get("priority", 50),
                -(x.get("current", 0) / x.get("required", 1) if x.get("required") else 0)
            ))
            missing_options = [x for x in options if not x["completed"]]
            available_missing_options = [
                x for x in missing_options
                if x.get("available", True)
            ]

            dependency_result.update({
                "current": current,
                "required": required,
                "remaining_required": remaining_required,
                "percent": round(current / required * 100, 1) if required else 0,
                "completed": completed,
                "options": options,
                "objectives": options,
                "completed_objectives": [x for x in options if x["completed"]],
                "missing_objectives": missing_options,
                "available": len(available_missing_options),
                "recommended_options": available_missing_options[:remaining_required]
            })

        if tracking == "shared_consumable":
            output_item_id = dependency.get("item_id")
            objective_required = dependency.get(
                "objective_required",
                1
            )
            shared_required = dependency.get(
                "shared_required",
                objective_required
            )
            output_owned = item_counts.get(
                output_item_id,
                0
            )

            objective_materials = []
            shared_materials = []

            for material in dependency.get(
                "per_unit_cost",
                []
            ):
                item_id = material["item_id"]
                owned = item_counts.get(item_id, 0)
                unit_count = material["count"]

                objective_required_count = (
                    unit_count * objective_required
                )
                shared_required_count = (
                    unit_count * shared_required
                )

                objective_missing = max(
                    objective_required_count - owned,
                    0
                )
                shared_missing = max(
                    shared_required_count - owned,
                    0
                )

                common = {
                    "item_id": item_id,
                    "name": material["name"],
                    "owned": owned,
                    "priority": material.get("priority", 50),
                    "activity": material.get("activity"),
                    "location": material.get("location"),
                    "minimum_minutes": material.get("minimum_minutes"),
                    "ideal_minutes": material.get("ideal_minutes"),
                    "action": material.get("action")
                }

                objective_materials.append({
                    **common,
                    "required": objective_required_count,
                    "missing": objective_missing,
                    "completed": objective_missing == 0
                })

                shared_materials.append({
                    **common,
                    "required": shared_required_count,
                    "missing": shared_missing,
                    "completed": shared_missing == 0
                })

            objective_materials.sort(
                key=lambda item: (
                    item["priority"],
                    -item["missing"]
                )
            )
            shared_materials.sort(
                key=lambda item: (
                    item["priority"],
                    -item["missing"]
                )
            )

            missing_objective_materials = [
                item
                for item in objective_materials
                if item["missing"] > 0
            ]
            missing_shared_materials = [
                item
                for item in shared_materials
                if item["missing"] > 0
            ]

            has_required_item = (
                output_owned >= objective_required
            )
            can_acquire_now = (
                not missing_objective_materials
            )

            blockers = []

            if not has_required_item:
                if missing_objective_materials:
                    blockers.extend(
                        {
                            "kind": "material",
                            **item
                        }
                        for item in missing_objective_materials
                    )
                else:
                    blockers.append({
                        "kind": "vendor_purchase",
                        "item_id": output_item_id,
                        "name": dependency["name"],
                        "required": objective_required,
                        "owned": output_owned,
                        "missing": max(
                            objective_required - output_owned,
                            0
                        ),
                        "activity": dependency.get(
                            "activity",
                            "vendor"
                        ),
                        "location": dependency.get("location"),
                        "minimum_minutes": dependency.get(
                            "minimum_minutes",
                            5
                        ),
                        "ideal_minutes": dependency.get(
                            "ideal_minutes",
                            10
                        ),
                        "action": dependency.get("action"),
                        "completed": False
                    })

            dependency_result.update({
                "item_id": output_item_id,
                "owned": output_owned,
                "current": min(
                    output_owned,
                    objective_required
                ),
                "required": objective_required,
                "objective_required": objective_required,
                "shared_required": shared_required,
                "shared_scope": dependency.get("shared_scope"),
                "percent": round(
                    min(output_owned, objective_required)
                    / objective_required
                    * 100,
                    1
                ) if objective_required else 0,
                "completed": has_required_item,
                "can_acquire_now": can_acquire_now,
                "ready_to_acquire": (
                    can_acquire_now
                    and not has_required_item
                ),
                "objective_materials": objective_materials,
                "missing_objective_materials": (
                    missing_objective_materials
                ),
                "shared_materials": shared_materials,
                "missing_shared_materials": (
                    missing_shared_materials
                ),
                "shared_primary_blocker": (
                    {
                        "kind": "shared_material",
                        **missing_shared_materials[0]
                    }
                    if missing_shared_materials
                    else None
                ),
                "objectives": blockers,
                "completed_objectives": [],
                "missing_objectives": blockers,
                "primary_blocker": (
                    blockers[0]
                    if blockers
                    else None
                )
            })

        if tracking == "crafting":
            output_item_id = dependency.get("item_id")
            output_required = dependency.get("required", 1)
            output_owned = item_counts.get(output_item_id, 0)

            material_totals = {}

            def add_material(material, count):
                item_id = material["item_id"]

                if item_id not in material_totals:
                    material_totals[item_id] = {
                        "item_id": item_id,
                        "name": material["name"],
                        "required": 0,
                        "priority": material.get("priority", 50),
                        "activity": material.get("activity"),
                        "location": material.get("location"),
                        "minimum_minutes": material.get("minimum_minutes"),
                        "ideal_minutes": material.get("ideal_minutes"),
                        "action": material.get("action")
                    }

                material_totals[item_id]["required"] += count

            for material in dependency.get("materials", []):
                add_material(material, material["required"])

            recipe_states = []

            for recipe in dependency.get("recipe_unlocks", []):
                unlocked = recipe["recipe_id"] in recipe_ids

                recipe_state = {
                    "recipe_id": recipe["recipe_id"],
                    "recipe_item_id": recipe.get("recipe_item_id"),
                    "name": recipe["name"],
                    "unlocked": unlocked,
                    "priority": recipe.get("priority", 50),
                    "activity": recipe.get("activity"),
                    "location": recipe.get("location"),
                    "minimum_minutes": recipe.get("minimum_minutes"),
                    "ideal_minutes": recipe.get("ideal_minutes"),
                    "action": recipe.get("action")
                }
                recipe_states.append(recipe_state)

                if not unlocked:
                    for cost in recipe.get("costs", []):
                        source = next(
                            (
                                material
                                for material in dependency.get("materials", [])
                                if material["item_id"] == cost["item_id"]
                            ),
                            {
                                "item_id": cost["item_id"],
                                "name": cost["name"]
                            }
                        )
                        add_material(source, cost["count"])

            materials = []

            for material in material_totals.values():
                owned = item_counts.get(material["item_id"], 0)
                missing = max(material["required"] - owned, 0)

                resolved = dict(material)
                resolved.update({
                    "owned": owned,
                    "missing": missing,
                    "completed": missing == 0
                })
                materials.append(resolved)

            materials.sort(
                key=lambda material: (
                    material["priority"],
                    -material["missing"]
                )
            )

            missing_materials = [
                material
                for material in materials
                if material["missing"] > 0
            ]

            missing_recipes = [
                recipe
                for recipe in recipe_states
                if not recipe["unlocked"]
            ]

            blockers = [
                {
                    "kind": "material",
                    **material
                }
                for material in missing_materials
            ]

            if not missing_materials:
                blockers.extend(
                    {
                        "kind": "recipe",
                        **recipe
                    }
                    for recipe in sorted(
                        missing_recipes,
                        key=lambda recipe: recipe["priority"]
                    )
                )

            ready_to_craft = (
                not missing_materials
                and not missing_recipes
                and output_owned < output_required
            )

            if ready_to_craft:
                blockers.append({
                    "kind": "craft",
                    "name": dependency["name"],
                    "activity": dependency.get("activity", "crafting"),
                    "location": dependency.get("location"),
                    "minimum_minutes": dependency.get("minimum_minutes", 5),
                    "ideal_minutes": dependency.get("ideal_minutes", 15),
                    "action": dependency.get("next_step", {}).get(
                        "note",
                        f"Craft {dependency['name']}."
                    )
                })

            required_nodes = len(materials) + len(recipe_states)
            completed_nodes = (
                sum(1 for material in materials if material["completed"])
                + sum(1 for recipe in recipe_states if recipe["unlocked"])
            )

            dependency_result.update({
                "item_id": output_item_id,
                "owned": output_owned,
                "current": completed_nodes,
                "required": required_nodes,
                "percent": round(
                    completed_nodes / required_nodes * 100,
                    1
                ) if required_nodes else 0,
                "completed": output_owned >= output_required,
                "recipe_id": dependency.get("recipe_id"),
                "recipe_known": (
                    dependency.get("recipe_id") in recipe_ids
                    if dependency.get("recipe_id") is not None
                    else True
                ),
                "materials": materials,
                "missing_materials": missing_materials,
                "recipe_unlocks": recipe_states,
                "missing_recipes": missing_recipes,
                "ready_to_craft": ready_to_craft,
                "objectives": blockers,
                "completed_objectives": [],
                "missing_objectives": blockers,
                "primary_blocker": blockers[0] if blockers else None
            })

        prerequisite = dependency.get(
            "prerequisite"
        )

        if prerequisite:
            dependency_result["prerequisite"] = (
                self._resolve_dependency(
                    dependency=prerequisite,
                    account_progress=account_progress,
                    item_counts=item_counts,
                    recipe_ids=recipe_ids
                )
            )
            dependency_result["blocked_by_prerequisite"] = (
                not dependency_result[
                    "prerequisite"
                ].get(
                    "completed",
                    False
                )
            )

        for field in (
            "time_gated",
            "time_gate",
            "sequential",
            "unlocks",
            "next_step",
            "reward",
            "completion_mode",
            "selection_mode",
            "available",
            "action",
            "activity",
            "location",
            "minimum_minutes",
            "ideal_minutes",
            "components",
            "option_noun",
            "options"
        ):
            if field in dependency:
                dependency_result[field] = dependency[field]

        if (
            dependency_result.get("sequential")
            and dependency_result.get("missing_objectives")
        ):
            dependency_result["next_objective"] = (
                dependency_result["missing_objectives"][0]
            )

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