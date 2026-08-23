import json
from pathlib import Path

from app.trackers.regalia import RegaliaTracker
from app.trackers.vision import VisionTracker
from app.trackers.aurora import AuroraTracker
from app.services.account_state import AccountState


class RecommendationService:

    MAX_RESULTS = 10
    MAX_PER_GOAL_ACTIVITY = 2

    def __init__(self):
        self.regalia = RegaliaTracker()
        self.vision = VisionTracker()
        self.aurora = AuroraTracker()

        game_data = (
            Path(__file__).parent.parent
            / "game_data"
        )

        with open(
            game_data / "acquisition.json",
            "r",
            encoding="utf-8"
        ) as file:
            self.acquisition = json.load(file)

        with open(
            game_data / "session_profiles.json",
            "r",
            encoding="utf-8"
        ) as file:
            self.session_profiles = json.load(file)

    async def get_recommendations(
        self,
        mode: str = "progress",
        goal: str | None = None,
        activity: str | None = None,
        minutes: int | None = None,
        full_candidate_pool: bool = False
    ):
        account_state = await AccountState.load()

        regalia = await self.regalia.progress(
            account_state=account_state
        )
        vision = await self.vision.progress(
            account_state=account_state
        )
        aurora = await self.aurora.progress(
            account_state=account_state
        )

        recommendations = []

        self._add_vision_recommendations(
            vision,
            recommendations
        )

        self._add_aurora_recommendations(
            aurora,
            recommendations
        )

        self._add_regalia_recommendations(
            regalia,
            recommendations
        )

        recommendations = self._consolidate_material_requirements(
            recommendations
        )

        recommendations = self._consolidate_achievement_dependencies(
            recommendations
        )

        recommendations = self._consolidate_shared_consumable_purchases(
            recommendations
        )

        for recommendation in recommendations:
            self._classify_activity(
                recommendation
            )

            self._add_session_profile(
                recommendation
            )

            self._score_recommendation(
                recommendation,
                mode
            )

            if minutes is not None:
                self._apply_time_fit(
                    recommendation,
                    minutes
                )

        recommendations.sort(
            key=lambda recommendation: recommendation["score"],
            reverse=True
        )

        candidate_count = len(recommendations)

        filtered = self._filter_recommendations(
            recommendations=recommendations,
            goal=goal,
            activity=activity
        )

        filtered_count = len(filtered)

        if minutes is not None:
            eligible = self._filter_by_time(
                recommendations=filtered,
                minutes=minutes
            )
        else:
            eligible = filtered

        eligible_count = len(eligible)

        if eligible:
            if full_candidate_pool:
                selected = list(eligible)
            else:
                selected = self._select_diverse_recommendations(
                    eligible,
                    mode
                )

            self._clean_internal_fields(
                selected
            )

            return {
                "mode": mode,
                "minutes": minutes,
                "filters": {
                    "goal": goal,
                    "activity": activity
                },
                "candidate_count": candidate_count,
                "filtered_count": filtered_count,
                "eligible_count": eligible_count,
                "match_found": True,
                "top_recommendation": (
                    selected[0]
                    if selected
                    else None
                ),
                "recommendations": selected
            }

        fallback = self._find_fallback(
            recommendations=recommendations,
            filtered=filtered,
            goal=goal,
            activity=activity,
            minutes=minutes
        )

        if fallback is not None:
            self._clean_internal_fields(
                [fallback]
            )

        if (
            minutes is not None
            and filtered
            and not eligible
        ):
            message = (
                "Recommendations matched the requested "
                "goal/activity filters, but none fit "
                f"within a {minutes}-minute session."
            )

        else:
            message = (
                "No direct recommendations matched "
                "the requested filters."
            )

        return {
            "mode": mode,
            "minutes": minutes,
            "filters": {
                "goal": goal,
                "activity": activity
            },
            "candidate_count": candidate_count,
            "filtered_count": filtered_count,
            "eligible_count": eligible_count,
            "match_found": False,
            "message": message,
            "fallback": fallback,
            "top_recommendation": None,
            "recommendations": []
        }

    def _consolidate_material_requirements(
        self,
        recommendations: list
    ):
        grouped = {}
        passthrough = []

        for recommendation in recommendations:
            item_id = recommendation.get("material_item_id")
            if item_id is None:
                passthrough.append(recommendation)
                continue

            key = (recommendation.get("goal"), item_id)
            grouped.setdefault(key, []).append(recommendation)

        consolidated = list(passthrough)

        for candidates in grouped.values():
            if len(candidates) == 1:
                consolidated.append(candidates[0])
                continue

            total_required = sum(
                candidate.get("material_required", 0)
                for candidate in candidates
            )
            owned_values = {
                candidate.get("material_owned", 0)
                for candidate in candidates
            }
            if len(owned_values) != 1:
                raise RuntimeError(
                    "Conflicting owned counts while consolidating material recommendations."
                )

            owned = owned_values.pop()
            missing = max(total_required - owned, 0)
            template = max(
                candidates,
                key=lambda candidate: (
                    1 if candidate.get("dependency") else 0,
                    candidate.get("material_required", 0)
                )
            )
            merged = dict(template)
            material_name = merged.get("material_name", "material")

            sources = []
            for candidate in candidates:
                source = candidate.get("material_source")
                if source and source not in sources:
                    sources.append(source)

            merged.update({
                "title": f"Acquire {missing} more {material_name}",
                "progress": f"{owned}/{total_required}",
                "progress_ratio": (owned / total_required if total_required else 1),
                "material_owned": owned,
                "material_required": total_required,
                "material_missing": missing,
                "material_sources": sources,
                "parent_objective": None,
                "reason": (
                    f"{total_required} {material_name} are required across "
                    f"{len(candidates)} Vision requirements; {owned} are currently owned."
                )
            })

            acquisition = self._get_acquisition_metadata(
                merged["material_item_id"]
            )
            if acquisition.get("activity"):
                merged["activity"] = acquisition["activity"]
            if acquisition.get("location"):
                merged["location"] = acquisition["location"]
            if acquisition.get("action"):
                merged["action"] = (
                    f"Acquire {missing} more {material_name}. "
                    f"{acquisition['action']}"
                )

            consolidated.append(merged)

        return consolidated

    def _consolidate_achievement_dependencies(
        self,
        recommendations: list
    ):
        grouped = {}
        passthrough = []

        for recommendation in recommendations:
            achievement_id = recommendation.get(
                "dependency_achievement_id"
            )

            if achievement_id is None:
                passthrough.append(recommendation)
                continue

            key = (
                recommendation.get("goal"),
                achievement_id
            )
            grouped.setdefault(key, []).append(
                recommendation
            )

        consolidated = list(passthrough)

        for candidates in grouped.values():
            if len(candidates) == 1:
                consolidated.append(candidates[0])
                continue

            template = max(
                candidates,
                key=lambda candidate: candidate.get(
                    "progress_ratio",
                    0
                )
            )
            merged = dict(template)

            parent_objectives = []
            for candidate in candidates:
                source = candidate.get(
                    "dependency_source"
                )
                if source and source not in parent_objectives:
                    parent_objectives.append(source)

            merged["parent_objectives"] = parent_objectives
            merged["shared_dependency_count"] = len(
                parent_objectives
            )

            achievement_name = next(
                (
                    candidate.get("dependency_achievement_name")
                    for candidate in candidates
                    if candidate.get("dependency_achievement_name")
                ),
                None
            )
            if achievement_name:
                merged["title"] = achievement_name

            merged.pop("parent_objective", None)
            merged.pop("dependency", None)
            merged.pop("dependency_chain", None)

            progress = merged.get("progress")
            source_text = (
                " and ".join(parent_objectives)
                if len(parent_objectives) <= 2
                else (
                    ", ".join(parent_objectives[:-1])
                    + f", and {parent_objectives[-1]}"
                )
            )

            merged["reason"] = (
                f"{merged['title']} advances "
                f"{len(parent_objectives)} Vision dependencies: "
                f"{source_text}."
                + (
                    f" Current progress is {progress}."
                    if progress
                    else ""
                )
            )

            consolidated.append(merged)

        return consolidated

    def _consolidate_shared_consumable_purchases(
        self,
        recommendations: list
    ):
        grouped = {}
        passthrough = []

        for recommendation in recommendations:
            dependency = recommendation.get("dependency") or {}

            if (
                dependency.get("tracking") != "shared_consumable"
                or dependency.get("item_id") is None
                or (dependency.get("primary_blocker") or {}).get("kind")
                != "vendor_purchase"
            ):
                passthrough.append(recommendation)
                continue

            key = (
                recommendation.get("goal"),
                dependency["item_id"]
            )
            grouped.setdefault(key, []).append(recommendation)

        consolidated = list(passthrough)

        for candidates in grouped.values():
            if len(candidates) == 1:
                consolidated.append(candidates[0])
                continue

            dependencies = [candidate["dependency"] for candidate in candidates]

            owned_values = {
                dependency.get("owned", 0)
                for dependency in dependencies
            }
            shared_required_values = {
                dependency.get("shared_required")
                for dependency in dependencies
            }

            if len(owned_values) != 1 or len(shared_required_values) != 1:
                consolidated.extend(candidates)
                continue

            owned = owned_values.pop()
            shared_required = shared_required_values.pop()

            immediate_required = sum(
                dependency.get("objective_required", 1)
                for dependency in dependencies
            )
            immediate_missing = max(immediate_required - owned, 0)

            template_dependency = dependencies[0]
            shared_materials = template_dependency.get("shared_materials", [])
            aggregate_materials = []
            can_acquire_all_now = True

            for material in shared_materials:
                shared_count = material.get("required", 0)
                per_unit = (
                    shared_count / shared_required
                    if shared_required
                    else 0
                )
                required = int(round(per_unit * immediate_missing))
                material_owned = material.get("owned", 0)
                missing = max(required - material_owned, 0)

                aggregate_materials.append({
                    **material,
                    "required": required,
                    "missing": missing,
                    "completed": missing == 0
                })

                if missing > 0:
                    can_acquire_all_now = False

            if not can_acquire_all_now:
                consolidated.extend(candidates)
                continue

            template = dict(candidates[0])
            dependency = dict(template_dependency)
            blocker = dict(dependency.get("primary_blocker") or {})

            parent_objectives = []
            for candidate in candidates:
                parent = candidate.get("parent_objective")
                if parent and parent not in parent_objectives:
                    parent_objectives.append(parent)

            blocker.update({
                "required": immediate_required,
                "owned": owned,
                "missing": immediate_missing
            })

            dependency.update({
                "progress": (
                    f"{min(owned, immediate_required)}/"
                    f"{immediate_required}"
                ),
                "current": min(owned, immediate_required),
                "required": immediate_required,
                "remaining_required": immediate_missing,
                "objective_required": immediate_required,
                "percent": round(
                    min(owned, immediate_required)
                    / immediate_required
                    * 100,
                    1
                ) if immediate_required else 0,
                "completed": owned >= immediate_required,
                "missing_count": 1 if immediate_missing > 0 else 0,
                "can_acquire_now": True,
                "ready_to_acquire": immediate_missing > 0,
                "objective_materials": aggregate_materials,
                "missing_objective_materials": [],
                "primary_blocker": blocker
            })

            item_name = dependency.get("name", "shared consumable")
            plural = "s" if immediate_missing != 1 else ""

            template.update({
                "title": (
                    f"Buy {immediate_missing} {item_name}{plural}"
                    if immediate_missing != 1
                    else f"Buy {item_name}"
                ),
                "parent_objectives": parent_objectives,
                "shared_dependency_count": len(parent_objectives),
                "dependency": dependency,
                "immediate_required": immediate_required,
                "immediate_missing": immediate_missing,
                "action": (
                    f"Buy {immediate_missing} {item_name}{plural} "
                    "from Alaleh at Chalon Docks to prepare the "
                    "currently modelled Vision of Enemies objectives."
                ),
                "reason": (
                    f"{len(parent_objectives)} incomplete Vision of Enemies "
                    f"objectives currently require {immediate_required} "
                    f"{item_name}{'s' if immediate_required != 1 else ''}; "
                    f"{owned} are currently owned. You have the materials "
                    f"needed to acquire all {immediate_missing} immediate "
                    f"requirement{'s' if immediate_missing != 1 else ''}. "
                    f"Across Vision of Enemies, {shared_required} are needed "
                    "in total."
                )
            })

            template.pop("parent_objective", None)
            consolidated.append(template)

        return consolidated

    def _filter_recommendations(
        self,
        recommendations: list,
        goal: str | None,
        activity: str | None
    ):
        filtered = recommendations

        if goal is not None:
            goal_names = {
                "vision": "Vision",
                "aurora": "Aurora",
                "regalia": "Prismatic Champion's Regalia"
            }

            wanted_goal = goal_names[goal]

            filtered = [
                recommendation
                for recommendation in filtered
                if recommendation["goal"] == wanted_goal
            ]

        if activity is not None:
            filtered = [
                recommendation
                for recommendation in filtered
                if recommendation["activity"] == activity
            ]

        return filtered

    def _filter_by_time(
        self,
        recommendations: list,
        minutes: int
    ):
        return [
            recommendation
            for recommendation in recommendations
            if recommendation["minimum_minutes"] <= minutes
        ]

    def _find_fallback(
        self,
        recommendations: list,
        filtered: list,
        goal: str | None,
        activity: str | None,
        minutes: int | None
    ):
        if minutes is not None:
            time_eligible = self._filter_by_time(
                recommendations=recommendations,
                minutes=minutes
            )
        else:
            time_eligible = recommendations

        if goal is not None:
            goal_candidates = self._filter_recommendations(
                recommendations=time_eligible,
                goal=goal,
                activity=None
            )

            if goal_candidates:
                return goal_candidates[0]

        if activity is not None:
            activity_candidates = self._filter_recommendations(
                recommendations=time_eligible,
                goal=None,
                activity=activity
            )

            if activity_candidates:
                return activity_candidates[0]

        if time_eligible:
            return time_eligible[0]

        if filtered:
            return filtered[0]

        if recommendations:
            return recommendations[0]

        return None

    def _clean_internal_fields(
        self,
        recommendations: list
    ):
        for recommendation in recommendations:
            recommendation.pop(
                "progress_ratio",
                None
            )

            recommendation.pop(
                "time_adjustment",
                None
            )

    def _select_diverse_recommendations(
        self,
        recommendations: list,
        mode: str
    ):
        if len(recommendations) <= self.MAX_RESULTS:
            return recommendations

        if mode != "play":
            return recommendations[:self.MAX_RESULTS]

        selected = []
        selected_ids = set()
        combination_counts = {}

        def combination_key(recommendation):
            return (
                recommendation["goal"],
                recommendation["activity"]
            )

        def can_add(recommendation):
            recommendation_id = id(
                recommendation
            )

            if recommendation_id in selected_ids:
                return False

            key = combination_key(
                recommendation
            )

            return (
                combination_counts.get(
                    key,
                    0
                )
                < self.MAX_PER_GOAL_ACTIVITY
            )

        def add_recommendation(
            recommendation
        ):
            if not can_add(
                recommendation
            ):
                return False

            recommendation_id = id(
                recommendation
            )

            key = combination_key(
                recommendation
            )

            selected.append(
                recommendation
            )

            selected_ids.add(
                recommendation_id
            )

            combination_counts[key] = (
                combination_counts.get(
                    key,
                    0
                ) + 1
            )

            return True

        add_recommendation(
            recommendations[0]
        )

        goals = []

        for recommendation in recommendations:
            goal_name = recommendation["goal"]

            if goal_name not in goals:
                goals.append(
                    goal_name
                )

        for goal_name in goals:
            if len(selected) >= self.MAX_RESULTS:
                break

            candidate = self._best_unselected_candidate(
                recommendations=recommendations,
                selected_ids=selected_ids,
                combination_counts=combination_counts,
                goal=goal_name
            )

            if candidate is not None:
                add_recommendation(
                    candidate
                )

        preferred_activities = [
            "open_world",
            "fractals",
            "wvw",
            "achievement",
            "crafting",
            "vendor",
            "trading_post",
            "acquisition"
        ]

        for activity_name in preferred_activities:
            if len(selected) >= self.MAX_RESULTS:
                break

            candidate = self._best_unselected_candidate(
                recommendations=recommendations,
                selected_ids=selected_ids,
                combination_counts=combination_counts,
                activity=activity_name
            )

            if candidate is not None:
                add_recommendation(
                    candidate
                )

        for recommendation in recommendations:
            if len(selected) >= self.MAX_RESULTS:
                break

            add_recommendation(
                recommendation
            )

        selected.sort(
            key=lambda recommendation: recommendation["score"],
            reverse=True
        )

        return selected

    def _best_unselected_candidate(
        self,
        recommendations: list,
        selected_ids: set,
        combination_counts: dict,
        goal: str | None = None,
        activity: str | None = None
    ):
        for recommendation in recommendations:
            if id(recommendation) in selected_ids:
                continue

            if (
                goal is not None
                and recommendation["goal"] != goal
            ):
                continue

            if (
                activity is not None
                and recommendation["activity"] != activity
            ):
                continue

            key = (
                recommendation["goal"],
                recommendation["activity"]
            )

            if (
                combination_counts.get(
                    key,
                    0
                )
                >= self.MAX_PER_GOAL_ACTIVITY
            ):
                continue

            return recommendation

        return None

    def _add_vision_recommendations(
        self,
        vision: dict,
        recommendations: list
    ):
        incomplete_without_objectives = []

        for stage in vision["stages"]:
            for collection in stage["collections"]:
                if collection["completed"]:
                    continue

                missing_objectives = collection.get(
                    "missing_objectives"
                )

                if missing_objectives is not None:
                    for objective in missing_objectives:
                        dependency_chain = objective.get(
                            "dependency"
                        )
                        dependency = (
                            self._active_vision_dependency(
                                dependency_chain
                            )
                            if dependency_chain
                            else None
                        )

                        if dependency:
                            required = dependency.get(
                                "required",
                                0
                            )

                            progress_ratio = (
                                dependency.get(
                                    "current",
                                    0
                                )
                                / required
                                if required
                                else 0
                            )

                            missing_dependency_objectives = (
                                dependency.get(
                                    "missing_objectives",
                                    []
                                )
                            )

                            remaining_required = max(
                                required - dependency.get("current", 0),
                                0
                            )

                            next_dependency_objective = (
                                dependency.get("next_objective")
                                if dependency.get("sequential")
                                else None
                            )

                            if dependency.get("completion_mode") == "threshold":
                                available = dependency.get(
                                    "available",
                                    len(dependency.get("objectives", []))
                                )
                                reason = (
                                    f"{dependency['name']} has "
                                    f"{dependency.get('current', 0)}/"
                                    f"{required} required unlocks. "
                                    f"Acquire {remaining_required} more "
                                    f"from {available} available options."
                                )
                            else:
                                reason = (
                                    f"{dependency['name']} is "
                                    f"{dependency.get('current', 0)}/"
                                    f"{required} complete, with "
                                    f"{len(missing_dependency_objectives)} "
                                    f"objectives remaining."
                                )

                            if next_dependency_objective:
                                reason += (
                                    " The dependency is sequential; "
                                    f"the next step is "
                                    f"{next_dependency_objective['name']}."
                                )

                            if dependency.get("time_gated"):
                                reason += (
                                    " Starting this time-gated dependency "
                                    "early avoids delaying later progress."
                                )
                        else:
                            progress_ratio = (
                                self._collection_progress_ratio(
                                    collection
                                )
                            )

                            missing_dependency_objectives = []

                            reason = (
                                f"This is an incomplete objective "
                                f"for {collection['name']}."
                            )

                        recommendation = {
                            "goal": "Vision",
                            "type": "objective",
                            "title": objective["name"],
                            "collection": collection["name"],
                            "collection_progress": (
                                f"{collection['current']}/"
                                f"{collection['max']}"
                            ),
                            "progress_ratio": progress_ratio,
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
                                "action",
                                (
                                    "Complete this objective "
                                    "for the collection."
                                )
                            ),
                            "reason": reason
                        }

                        if dependency:
                            recommendation["time_gated"] = (
                                dependency.get("time_gated", False)
                            )
                            recommendation["time_gate"] = (
                                dependency.get("time_gate")
                            )

                            next_dependency_objective = (
                                dependency.get("next_objective")
                                if dependency.get("sequential")
                                else None
                            )

                            if next_dependency_objective:
                                recommendation["parent_objective"] = (
                                    objective["name"]
                                )
                                recommendation[
                                    "dependency_achievement_id"
                                ] = dependency.get("achievement_id")
                                recommendation[
                                    "dependency_achievement_name"
                                ] = dependency.get("name")
                                recommendation[
                                    "dependency_source"
                                ] = objective["name"]
                                recommendation["title"] = (
                                    f"{dependency['name']}: "
                                    f"{next_dependency_objective['name']}"
                                )
                                recommendation["location"] = (
                                    next_dependency_objective.get(
                                        "location",
                                        objective.get("location")
                                    )
                                )
                                recommendation["minimum_minutes"] = (
                                    next_dependency_objective.get(
                                        "minimum_minutes",
                                        objective.get("minimum_minutes")
                                    )
                                )
                                recommendation["ideal_minutes"] = (
                                    next_dependency_objective.get(
                                        "ideal_minutes",
                                        objective.get("ideal_minutes")
                                    )
                                )
                                recommendation["action"] = (
                                    next_dependency_objective.get(
                                        "action",
                                        objective.get("action")
                                    )
                                )

                            if (
                                dependency.get("completion_mode")
                                == "threshold"
                                and dependency.get("selection_mode")
                                == "any"
                            ):
                                missing_options = (
                                    missing_dependency_objectives
                                )
                                representative = (
                                    missing_options[0]
                                    if missing_options
                                    else {}
                                )

                                recommendation["parent_objective"] = (
                                    objective["name"]
                                )
                                plural = (
                                    "s" if remaining_required != 1 else ""
                                )
                                option_noun = dependency.get(
                                    "option_noun",
                                    "Dragonsblood weapon skin"
                                )
                                if (
                                    dependency.get("tracking")
                                    == "achievement_options"
                                    and representative
                                ):
                                    recommendation["title"] = (
                                        f"{dependency['name']}: "
                                        f"{representative['name']}"
                                    )
                                else:
                                    recommendation["title"] = (
                                        f"{dependency['name']}: Acquire "
                                        f"{remaining_required} more "
                                        f"{option_noun}{plural}"
                                    )
                                recommendation["activity"] = (
                                    representative.get(
                                        "activity",
                                        objective.get("activity")
                                    )
                                )
                                recommendation["location"] = (
                                    representative.get(
                                        "location",
                                        objective.get("location")
                                    )
                                )
                                recommendation["minimum_minutes"] = (
                                    representative.get(
                                        "minimum_minutes",
                                        objective.get("minimum_minutes")
                                    )
                                )
                                recommendation["ideal_minutes"] = (
                                    representative.get(
                                        "ideal_minutes",
                                        objective.get("ideal_minutes")
                                    )
                                )
                                if (
                                    dependency.get("tracking")
                                    == "achievement_options"
                                    and representative
                                ):
                                    recommendation["action"] = (
                                        representative.get(
                                            "action",
                                            objective.get("action")
                                        )
                                    )
                                    recommendation["reason"] = (
                                        f"{dependency['name']} is "
                                        f"{dependency.get('current', 0)}/"
                                        f"{dependency.get('required', 0)}. "
                                        f"Complete {remaining_required} more "
                                        f"{option_noun}{plural}; "
                                        f"{representative.get('name')} is "
                                        "currently the highest-priority option."
                                    )
                                else:
                                    recommendation["action"] = (
                                        f"Unlock any {remaining_required} of the "
                                        f"{len(missing_options)} remaining "
                                        f"{option_noun}{plural}."
                                    )
                                recommendation["options"] = (
                                    missing_options
                                )

                            if dependency.get("tracking") == "shared_consumable":
                                blocker = dependency.get("primary_blocker")
                                shared_blocker = dependency.get("shared_primary_blocker")

                                recommendation["parent_objective"] = objective["name"]

                                if blocker:
                                    if blocker.get("kind") == "material":
                                        recommendation["title"] = (
                                            f"Acquire {blocker['missing']} more {blocker['name']}"
                                        )
                                    elif blocker.get("kind") == "vendor_purchase":
                                        recommendation["title"] = (
                                            f"Buy {blocker['name']}"
                                        )
                                    else:
                                        recommendation["title"] = blocker.get(
                                            "name",
                                            objective["name"]
                                        )

                                    recommendation["activity"] = blocker.get(
                                        "activity",
                                        objective.get("activity")
                                    )
                                    recommendation["location"] = blocker.get(
                                        "location",
                                        objective.get("location")
                                    )
                                    recommendation["minimum_minutes"] = blocker.get(
                                        "minimum_minutes",
                                        objective.get("minimum_minutes")
                                    )
                                    recommendation["ideal_minutes"] = blocker.get(
                                        "ideal_minutes",
                                        objective.get("ideal_minutes")
                                    )
                                    recommendation["action"] = blocker.get(
                                        "action",
                                        objective.get("action")
                                    )
                                    recommendation["event_dependent"] = blocker.get(
                                        "event_dependent",
                                        False
                                    )

                                reason = (
                                    f"{objective['name']} requires "
                                    f"{dependency['objective_required']} "
                                    f"{dependency['name']}."
                                )

                                if dependency.get("ready_to_acquire"):
                                    reason += (
                                        " You already have the materials "
                                        "needed for this objective."
                                    )

                                if shared_blocker:
                                    reason += (
                                        f" Across {dependency.get('shared_scope', 'Vision')}, "
                                        f"{dependency['shared_required']} are needed in total; "
                                        f"you still need {shared_blocker['missing']} more "
                                        f"{shared_blocker['name']} for the full shared requirement."
                                    )

                                recommendation["reason"] = reason

                            if dependency.get("tracking") == "crafting":
                                blocker = dependency.get("primary_blocker")

                                recommendation["parent_objective"] = (
                                    objective["name"]
                                )

                                if blocker:
                                    acquisition = self.acquisition.get(
                                        str(blocker.get("item_id")),
                                        {}
                                    )

                                    if blocker.get("kind") == "material":
                                        recommendation["title"] = (
                                            f"Acquire {blocker['missing']} more "
                                            f"{blocker['name']}"
                                        )
                                        recommendation["material_item_id"] = blocker["item_id"]
                                        recommendation["material_name"] = blocker["name"]
                                        recommendation["material_owned"] = blocker["owned"]
                                        recommendation["material_required"] = blocker["required"]
                                        recommendation["material_source"] = objective["name"]
                                    else:
                                        recommendation["title"] = blocker["name"]

                                    recommendation["activity"] = (
                                        acquisition.get(
                                            "activity",
                                            blocker.get(
                                                "activity",
                                                objective.get("activity")
                                            )
                                        )
                                    )
                                    recommendation["location"] = (
                                        acquisition.get(
                                            "location",
                                            blocker.get(
                                                "location",
                                                objective.get("location")
                                            )
                                        )
                                    )
                                    recommendation["minimum_minutes"] = (
                                        blocker.get(
                                            "minimum_minutes",
                                            objective.get("minimum_minutes")
                                        )
                                    )
                                    recommendation["ideal_minutes"] = (
                                        blocker.get(
                                            "ideal_minutes",
                                            objective.get("ideal_minutes")
                                        )
                                    )

                                    acquisition_action = acquisition.get("action")
                                    blocker_action = blocker.get("action")

                                    if (
                                        blocker.get("kind") == "material"
                                        and acquisition_action
                                    ):
                                        recommendation["action"] = (
                                            f"Acquire {blocker['missing']} more "
                                            f"{blocker['name']}. "
                                            f"{acquisition_action}"
                                        )
                                    else:
                                        recommendation["action"] = (
                                            blocker_action
                                            or objective.get("action")
                                        )

                                missing_materials = dependency.get(
                                    "missing_materials",
                                    []
                                )
                                missing_recipes = dependency.get(
                                    "missing_recipes",
                                    []
                                )

                                recommendation["reason"] = (
                                    f"{dependency['name']} has "
                                    f"{len(missing_materials)} material "
                                    f"shortage(s) and "
                                    f"{len(missing_recipes)} locked "
                                    "recipe(s) remaining."
                                )

                            recommendation["dependency"] = {
                                "achievement_id": dependency.get(
                                    "achievement_id"
                                ),
                                "name": dependency.get(
                                    "name"
                                ),
                                "progress": (
                                    f"{dependency.get('current', 0)}/"
                                    f"{required}"
                                ),
                                "current": dependency.get(
                                    "current",
                                    0
                                ),
                                "required": required,
                                "percent": dependency.get(
                                    "percent"
                                ),
                                "completed": dependency.get(
                                    "completed",
                                    False
                                ),
                                "missing_count": len(
                                    missing_dependency_objectives
                                ),
                                "missing_objectives": (
                                    missing_dependency_objectives
                                ),
                                "alternative": dependency.get(
                                    "alternative"
                                ),
                                "time_gated": dependency.get(
                                    "time_gated",
                                    False
                                ),
                                "time_gate": dependency.get(
                                    "time_gate"
                                ),
                                "sequential": dependency.get(
                                    "sequential",
                                    False
                                ),
                                "next_objective": dependency.get(
                                    "next_objective"
                                ),
                                "unlocks": dependency.get(
                                    "unlocks"
                                ),
                                "next_step": dependency.get(
                                    "next_step"
                                ),
                                "completion_mode": dependency.get(
                                    "completion_mode"
                                ),
                                "selection_mode": dependency.get(
                                    "selection_mode"
                                ),
                                "available": dependency.get(
                                    "available"
                                ),
                                "remaining_required": remaining_required,
                                "tracking": dependency.get("tracking"),
                                "item_id": dependency.get("item_id"),
                                "owned": dependency.get("owned"),
                                "recipe_id": dependency.get("recipe_id"),
                                "recipe_known": dependency.get("recipe_known"),
                                "materials": dependency.get("materials"),
                                "missing_materials": dependency.get(
                                    "missing_materials"
                                ),
                                "recipe_unlocks": dependency.get(
                                    "recipe_unlocks"
                                ),
                                "missing_recipes": dependency.get(
                                    "missing_recipes"
                                ),
                                "ready_to_craft": dependency.get(
                                    "ready_to_craft"
                                ),
                                "primary_blocker": dependency.get(
                                    "primary_blocker"
                                ),
                                "objective_required": dependency.get(
                                    "objective_required"
                                ),
                                "shared_required": dependency.get(
                                    "shared_required"
                                ),
                                "shared_scope": dependency.get(
                                    "shared_scope"
                                ),
                                "can_acquire_now": dependency.get(
                                    "can_acquire_now"
                                ),
                                "ready_to_acquire": dependency.get(
                                    "ready_to_acquire"
                                ),
                                "objective_materials": dependency.get(
                                    "objective_materials"
                                ),
                                "missing_objective_materials": dependency.get(
                                    "missing_objective_materials"
                                ),
                                "shared_materials": dependency.get(
                                    "shared_materials"
                                ),
                                "missing_shared_materials": dependency.get(
                                    "missing_shared_materials"
                                ),
                                "shared_primary_blocker": dependency.get(
                                    "shared_primary_blocker"
                                ),
                                "recommended_options": dependency.get(
                                    "recommended_options"
                                ),
                                "option_noun": dependency.get("option_noun")
                            }

                        if (
                            dependency_chain
                            and dependency_chain is not dependency
                        ):
                            recommendation["dependency_chain"] = (
                                dependency_chain
                            )

                        if (
                            dependency
                            and dependency.get("tracking")
                            == "achievement_options"
                            and dependency.get("completion_mode")
                            == "threshold"
                            and dependency.get("selection_mode")
                            == "any"
                        ):
                            missing_options = dependency.get(
                                "missing_objectives",
                                []
                            )
                            remaining_required = dependency.get(
                                "remaining_required",
                                max(
                                    dependency.get("required", 0)
                                    - dependency.get("current", 0),
                                    0
                                )
                            )

                            option_window = min(
                                len(missing_options),
                                max(
                                    remaining_required * 2,
                                    remaining_required,
                                    1
                                )
                            )

                            for option_index, option in enumerate(
                                missing_options[:option_window]
                            ):
                                option_recommendation = dict(
                                    recommendation
                                )

                                option_recommendation["title"] = (
                                    f"{dependency['name']}: "
                                    f"{option['name']}"
                                )
                                option_recommendation[
                                    "parent_objective"
                                ] = objective["name"]
                                option_recommendation["activity"] = (
                                    option.get(
                                        "activity",
                                        objective.get("activity")
                                    )
                                )
                                option_recommendation["location"] = (
                                    option.get(
                                        "location",
                                        objective.get("location")
                                    )
                                )
                                option_recommendation[
                                    "minimum_minutes"
                                ] = option.get(
                                    "minimum_minutes",
                                    objective.get("minimum_minutes")
                                )
                                option_recommendation[
                                    "ideal_minutes"
                                ] = option.get(
                                    "ideal_minutes",
                                    objective.get("ideal_minutes")
                                )
                                option_recommendation["action"] = (
                                    option.get(
                                        "action",
                                        objective.get("action")
                                    )
                                )
                                option_recommendation[
                                    "event_dependent"
                                ] = option.get(
                                    "event_dependent",
                                    False
                                )
                                option_recommendation[
                                    "dependency_option"
                                ] = option
                                option_recommendation[
                                    "dependency_achievement_id"
                                ] = option.get("achievement_id")
                                option_recommendation[
                                    "dependency_achievement_name"
                                ] = option.get("name")
                                option_recommendation[
                                    "dependency_source"
                                ] = objective["name"]
                                option_recommendation[
                                    "dependency_option_rank"
                                ] = option_index + 1
                                option_recommendation[
                                    "score_adjustment"
                                ] = (
                                    -4
                                    if option.get(
                                        "event_dependent",
                                        False
                                    )
                                    else 0
                                )

                                option_recommendation["reason"] = (
                                    f"{dependency['name']} is "
                                    f"{dependency.get('current', 0)}/"
                                    f"{dependency.get('required', 0)}. "
                                    f"Complete {remaining_required} more "
                                    f"{dependency.get('option_noun', 'option')}"
                                    f"{'s' if remaining_required != 1 else ''}. "
                                    f"{option['name']} is one of the "
                                    "highest-priority remaining options."
                                )

                                option_required = option.get("required")
                                if option_required:
                                    option_recommendation["progress"] = (
                                        f"{option.get('current', 0)}/"
                                        f"{option_required}"
                                    )
                                    option_recommendation[
                                        "option_progress_ratio"
                                    ] = (
                                        option.get("current", 0)
                                        / option_required
                                    )

                                recommendations.append(
                                    option_recommendation
                                )

                            continue

                        if (
                            dependency
                            and dependency.get("tracking")
                            in {"achievement_bits", "achievement_set"}
                        ):
                            for child in missing_dependency_objectives:
                                child_achievement_id = child.get(
                                    "achievement_id"
                                )

                                if child_achievement_id is None:
                                    continue

                                child_recommendation = dict(
                                    recommendation
                                )
                                child_recommendation.update({
                                    "type": "objective",
                                    "title": child["name"],
                                    "parent_objective": objective["name"],
                                    "dependency_achievement_id": (
                                        child_achievement_id
                                    ),
                                    "dependency_source": objective["name"],
                                    "activity": child.get(
                                        "activity",
                                        objective.get("activity")
                                    ),
                                    "location": child.get(
                                        "location",
                                        objective.get("location")
                                    ),
                                    "minimum_minutes": child.get(
                                        "minimum_minutes",
                                        objective.get("minimum_minutes")
                                    ),
                                    "ideal_minutes": child.get(
                                        "ideal_minutes",
                                        objective.get("ideal_minutes")
                                    ),
                                    "action": child.get(
                                        "action",
                                        objective.get("action")
                                    ),
                                    "event_dependent": child.get(
                                        "event_dependent",
                                        False
                                    ),
                                    "reason": (
                                        f"{child['name']} is required for "
                                        f"{objective['name']}."
                                    )
                                })

                                child_required = child.get(
                                    "required"
                                )

                                if child_required:
                                    child_current = child.get(
                                        "current",
                                        0
                                    )
                                    child_recommendation["progress"] = (
                                        f"{child_current}/{child_required}"
                                    )
                                    child_recommendation[
                                        "progress_ratio"
                                    ] = (
                                        child_current
                                        / child_required
                                    )

                                recommendations.append(
                                    child_recommendation
                                )

                        recommendations.append(
                            recommendation
                        )

                    continue

                if (
                    collection.get("tracking") == "count_only"
                    and not collection.get(
                        "prerequisite_met",
                        collection.get("unlocked", True)
                    )
                ):
                    continue

                incomplete_without_objectives.append(
                    collection
                )

        if incomplete_without_objectives:
            best_collection = max(
                incomplete_without_objectives,
                key=self._collection_progress_ratio
            )

            if best_collection.get("tracking") == "count_only":
                recommendations.append({
                    "goal": "Vision",
                    "type": "achievement",
                    "title": (
                        f"Continue "
                        f"{best_collection['name']}"
                    ),
                    "progress": (
                        f"{best_collection['current']}/"
                        f"{best_collection['max']}"
                    ),
                    "progress_ratio": (
                        self._collection_progress_ratio(
                            best_collection
                        )
                    ),
                    "activity": best_collection.get(
                        "activity"
                    ),
                    "minimum_minutes": best_collection.get(
                        "minimum_minutes"
                    ),
                    "ideal_minutes": best_collection.get(
                        "ideal_minutes"
                    ),
                    "action": best_collection.get(
                        "action",
                        "Continue progressing this achievement."
                    ),
                    "reason": (
                        "This Vision achievement is unlocked "
                        "and is tracked by completion count."
                    )
                })
            else:
                recommendations.append({
                    "goal": "Vision",
                    "type": "achievement",
                    "title": (
                        f"Continue "
                        f"{best_collection['name']}"
                    ),
                    "progress": (
                        f"{best_collection['current']}/"
                        f"{best_collection['max']}"
                    ),
                    "progress_ratio": (
                        self._collection_progress_ratio(
                            best_collection
                        )
                    ),
                    "action": (
                        "Continue the incomplete "
                        "collection objectives."
                    ),
                    "reason": (
                        "This is your most-progressed "
                        "incomplete Vision collection "
                        "without objective-level data."
                    )
                })

        missing_materials = (
            vision
            .get("summary", {})
            .get("missing_materials", [])
        )

        for material in missing_materials:
            if not self._is_directly_recommendable(
                material["id"]
            ):
                continue

            metadata = self._get_acquisition_metadata(
                material["id"]
            )

            recommendations.append({
                "goal": "Vision",
                "type": metadata.get(
                    "type",
                    "material"
                ),
                "material_item_id": material["id"],
                "material_name": material["name"],
                "material_owned": material["owned"],
                "material_required": material["required"],
                "material_source": "Vision crafting requirements",
                "title": (
                    f"Acquire {material['missing']} "
                    f"more {material['name']}"
                ),
                "progress": (
                    f"{material['owned']}/"
                    f"{material['required']}"
                ),
                "progress_ratio": (
                    self._material_progress_ratio(
                        material
                    )
                ),
                "activity": metadata.get(
                    "activity"
                ),
                "location": metadata.get(
                    "location"
                ),
                "minimum_minutes": metadata.get(
                    "minimum_minutes"
                ),
                "ideal_minutes": metadata.get(
                    "ideal_minutes"
                ),
                "action": metadata.get(
                    "action",
                    "Acquire the remaining "
                    "required amount."
                ),
                "reason": (
                    "This material is still "
                    "required for Vision."
                )
            })

    def _active_vision_dependency(
        self,
        dependency: dict
    ):
        active = dependency

        while active:
            prerequisite = active.get(
                "prerequisite"
            )

            if (
                not prerequisite
                or prerequisite.get(
                    "completed",
                    False
                )
            ):
                return active

            active = prerequisite

        return dependency

    def _add_aurora_recommendations(
        self,
        aurora: dict,
        recommendations: list
    ):
        summary = aurora.get("summary", {})
        status = summary.get("status")

        if status == "locked":
            next_step = summary.get("next_step", {})
            unlock = next_step.get("unlock")

            if unlock:
                required = unlock.get("required", 0)
                current = unlock.get("current", 0)
                progress_ratio = (
                    current / required
                    if required
                    else 0
                )
                missing_requirements = unlock.get(
                    "missing_requirements",
                    []
                )

                if missing_requirements:
                    for requirement in missing_requirements:
                        reward_name = requirement.get(
                            "reward_item_name"
                        )

                        reason = (
                            f"Aurora: Awakening is locked. "
                            f"The Sentient Seed prerequisite "
                            f"is {current}/{required} complete."
                        )

                        if reward_name:
                            reason += (
                                f" Completing this awards "
                                f"{reward_name}."
                            )

                        objective_progress = requirement.get(
                            "objective_progress"
                        )

                        if objective_progress:
                            objective_required = objective_progress.get(
                                "required",
                                0
                            )
                            objective_current = objective_progress.get(
                                "current",
                                0
                            )
                            objective_ratio = (
                                objective_current / objective_required
                                if objective_required
                                else 0
                            )

                            for group in objective_progress.get(
                                "missing_groups",
                                []
                            ):
                                group_objectives = group.get(
                                    "objectives",
                                    []
                                )

                                requirement_name = requirement["name"]
                                requirement_location = requirement.get(
                                    "location"
                                )

                                recommendations.append({
                                    "goal": "Aurora",
                                    "type": "objective_bundle",
                                    "title": (
                                        f"{requirement_name}: "
                                        f"{group['name']}"
                                    ),
                                    "progress": (
                                        f"{objective_current}/"
                                        f"{objective_required}"
                                    ),
                                    "progress_ratio": objective_ratio,
                                    "activity": "open_world",
                                    "location": requirement_location,
                                    "minimum_minutes": max(
                                        5,
                                        len(group_objectives) * 2
                                    ),
                                    "ideal_minutes": max(
                                        10,
                                        len(group_objectives) * 5
                                    ),
                                    "action": (
                                        f"Complete the "
                                        f"{len(group_objectives)} missing "
                                        f"{requirement_name} objective(s) "
                                        f"in {group['name']}."
                                    ),
                                    "reason": (
                                        f"{requirement_name} is "
                                        f"{objective_current}/"
                                        f"{objective_required} complete. "
                                        f"This keeps the work grouped within "
                                        f"{group['name']}"
                                        + (
                                            f" in {requirement_location}."
                                            if requirement_location
                                            else "."
                                        )
                                    ),
                                    "objectives": group_objectives,
                                    "unlock": {
                                        "stage": next_step.get("stage"),
                                        "name": unlock.get("name"),
                                        "progress": f"{current}/{required}",
                                        "percent": unlock.get("percent"),
                                        "reward_item_id": requirement.get(
                                            "reward_item_id"
                                        ),
                                        "reward_item_name": reward_name
                                    }
                                })

                            continue

                        recommendations.append({
                            "goal": "Aurora",
                            "type": "unlock_requirement",
                            "title": requirement["name"],
                            "progress": f"{current}/{required}",
                            "progress_ratio": progress_ratio,
                            "activity": requirement.get("activity"),
                            "location": requirement.get("location"),
                            "minimum_minutes": requirement.get(
                                "minimum_minutes"
                            ),
                            "ideal_minutes": requirement.get(
                                "ideal_minutes"
                            ),
                            "action": requirement.get(
                                "action",
                                "Complete this prerequisite for Aurora: Awakening."
                            ),
                            "reason": reason,
                            "unlock": {
                                "stage": next_step.get("stage"),
                                "name": unlock.get("name"),
                                "progress": f"{current}/{required}",
                                "percent": unlock.get("percent"),
                                "reward_item_id": requirement.get(
                                    "reward_item_id"
                                ),
                                "reward_item_name": reward_name
                            }
                        })

                    return

                combine = unlock.get("combine", {})
                purchase = unlock.get("purchase", {})

                recommendations.append({
                    "goal": "Aurora",
                    "type": "unlock",
                    "title": f"Acquire {unlock['name']}",
                    "progress": f"{current}/{required}",
                    "progress_ratio": progress_ratio,
                    "activity": "vendor",
                    "minimum_minutes": 5,
                    "ideal_minutes": 10,
                    "action": " ".join(
                        part
                        for part in (
                            combine.get("action"),
                            purchase.get("action")
                        )
                        if part
                    ),
                    "reason": (
                        "All tracked sentient-item prerequisites are complete. "
                        "Finish the Sentient Seed unlock to open Aurora: Awakening."
                    ),
                    "unlock": {
                        "stage": next_step.get("stage"),
                        "name": unlock.get("name"),
                        "progress": f"{current}/{required}",
                        "percent": unlock.get("percent"),
                        "combine": combine,
                        "purchase": purchase
                    }
                })

                return

            if next_step:
                recommendations.append({
                    "goal": "Aurora",
                    "type": "unlock",
                    "title": f"Unlock {next_step['stage']}",
                    "progress_ratio": 0,
                    "action": (
                        "Complete the prerequisite needed to unlock this "
                        "Aurora stage."
                    ),
                    "reason": "Aurora progression is currently locked."
                })

            return

        incomplete_collections = []

        for stage in aurora["stages"]:
            if stage["status"] == "locked":
                continue

            for collection in stage["collections"]:
                if collection["completed"]:
                    continue

                if not collection.get("actionable", True):
                    continue

                objective_progress = collection.get(
                    "objective_progress"
                )

                if objective_progress:
                    objective_required = objective_progress.get(
                        "required",
                        collection.get("max", 0)
                    )
                    objective_current = objective_progress.get(
                        "current",
                        collection.get("current", 0)
                    )
                    objective_ratio = (
                        objective_current / objective_required
                        if objective_required
                        else 0
                    )

                    for group in objective_progress.get(
                        "missing_groups",
                        []
                    ):
                        group_objectives = group.get(
                            "objectives",
                            []
                        )

                        if not group_objectives:
                            continue

                        minimum_minutes = sum(
                            objective.get(
                                "minimum_minutes",
                                5
                            )
                            for objective in group_objectives
                        )
                        ideal_minutes = sum(
                            objective.get(
                                "ideal_minutes",
                                10
                            )
                            for objective in group_objectives
                        )

                        activities = {
                            objective.get(
                                "activity",
                                "open_world"
                            )
                            for objective in group_objectives
                        }
                        bundle_activity = (
                            next(iter(activities))
                            if len(activities) == 1
                            else "open_world"
                        )

                        recommendations.append({
                            "goal": "Aurora",
                            "type": "objective_bundle",
                            "title": (
                                f"{collection['name']}: "
                                f"{group['name']}"
                            ),
                            "progress": (
                                f"{objective_current}/"
                                f"{objective_required}"
                            ),
                            "progress_ratio": objective_ratio,
                            "activity": bundle_activity,
                            "location": collection.get(
                                "location"
                            ),
                            "minimum_minutes": max(
                                5,
                                minimum_minutes
                            ),
                            "ideal_minutes": max(
                                10,
                                ideal_minutes
                            ),
                            "action": (
                                f"Work on the "
                                f"{len(group_objectives)} missing "
                                f"{group['name'].lower()} "
                                f"objective(s) for "
                                f"{collection['name']}."
                            ),
                            "reason": (
                                f"{collection['name']} is "
                                f"{objective_current}/"
                                f"{objective_required} complete. "
                                f"This groups similar work in "
                                f"{collection.get('location')}."
                            ),
                            "objectives": group_objectives
                        })

                    continue

                incomplete_collections.append(collection)

        if incomplete_collections:
            best_collection = max(
                incomplete_collections,
                key=self._collection_progress_ratio
            )

            recommendations.append({
                "goal": "Aurora",
                "type": "achievement",
                "title": f"Continue {best_collection['name']}",
                "progress": (
                    f"{best_collection['current']}/"
                    f"{best_collection['max']}"
                ),
                "progress_ratio": (
                    self._collection_progress_ratio(best_collection)
                ),
                "action": (
                    "Continue the incomplete collection objectives."
                ),
                "reason": (
                    "This is your most-progressed incomplete "
                    "Aurora collection without objective-level guidance."
                )
            })

    def _add_regalia_recommendations(
        self,
        regalia: dict,
        recommendations: list
    ):
        incomplete_steps = [
            step
            for step in regalia["steps"]
            if not step["completed"]
        ]

        if not incomplete_steps:
            return

        next_step = incomplete_steps[0]

        if next_step.get("id") == 5960:
            dependency = regalia.get("dependency", {})
            resolved = dependency.get("next_step")

            if resolved:
                remaining = [
                    item
                    for item in dependency.get("chain", [])
                    if not item["completed"]
                ]

                recommendations.append({
                    "goal": "Prismatic Champion's Regalia",
                    "type": "unlock_requirement",
                    "title": resolved["name"],
                    "progress_ratio": 0,
                    "activity": resolved.get("activity", "achievement"),
                    "location": resolved.get("location"),
                    "minimum_minutes": resolved.get("minimum_minutes"),
                    "ideal_minutes": resolved.get("ideal_minutes"),
                    "action": resolved.get(
                        "action",
                        "Complete this prerequisite."
                    ),
                    "reason": (
                        "End Conjecture is locked behind this "
                        f"achievement chain. {len(remaining)} "
                        "tracked step(s) remain."
                    ),
                    "dependency": dependency
                })
                return

        recommendations.append({
            "goal": "Prismatic Champion's Regalia",
            "type": "achievement",
            "title": next_step["name"],
            "progress_ratio": 0,
            "action": "Complete this Return achievement.",
            "reason": (
                "This is the next incomplete Regalia achievement "
                "in the tracked list."
            )
        })

    def _classify_activity(
        self,
        recommendation: dict
    ):
        if recommendation.get(
            "activity"
        ):
            return

        recommendation_type = (
            recommendation["type"]
        )

        activity_types = {
            "objective": "achievement",
            "achievement": "achievement",
            "unlock": "achievement",
            "unlock_requirement": "achievement",
            "achievement_reward": "achievement",
            "wvw_or_buy": "wvw",
            "fractals_or_buy": "fractals",
            "vendor": "vendor",
            "trading_post": "trading_post",
            "open_world": "open_world",
            "material": "acquisition"
        }

        recommendation["activity"] = (
            activity_types.get(
                recommendation_type,
                "other"
            )
        )

    def _add_session_profile(
        self,
        recommendation: dict
    ):
        if (
            recommendation.get("minimum_minutes") is not None
            and recommendation.get("ideal_minutes") is not None
        ):
            return

        activity = recommendation[
            "activity"
        ]

        profile = self.session_profiles.get(
            activity,
            self.session_profiles["other"]
        )

        if recommendation.get("minimum_minutes") is None:
            recommendation["minimum_minutes"] = (
                profile["minimum_minutes"]
            )

        if recommendation.get("ideal_minutes") is None:
            recommendation["ideal_minutes"] = (
                profile["ideal_minutes"]
            )

    def _apply_time_fit(
        self,
        recommendation: dict,
        minutes: int
    ):
        minimum = recommendation[
            "minimum_minutes"
        ]

        ideal = recommendation[
            "ideal_minutes"
        ]

        if minutes >= ideal:
            time_adjustment = 30
            label = "excellent"

        elif minutes >= minimum:
            range_size = (
                ideal - minimum
            )

            if range_size <= 0:
                fit_ratio = 1
            else:
                fit_ratio = (
                    (minutes - minimum)
                    / range_size
                )

            time_adjustment = (
                15
                + (fit_ratio * 10)
            )

            label = "good"

        else:
            shortage_ratio = (
                minutes / minimum
            )

            time_adjustment = (
                -50
                + (shortage_ratio * 30)
            )

            label = "limited"

        recommendation["time_fit"] = (
            label
        )

        recommendation["time_adjustment"] = round(
            time_adjustment,
            1
        )

        recommendation["score"] = round(
            recommendation["score"]
            + time_adjustment,
            1
        )

    def _score_recommendation(
        self,
        recommendation: dict,
        mode: str
    ):
        recommendation_type = (
            recommendation["type"]
        )

        value_scores = {
            "objective": 105,
            "objective_bundle": 100,
            "achievement": 100,
            "unlock_requirement": 100,
            "unlock": 95,
            "achievement_reward": 90,
            "open_world": 75,
            "wvw_or_buy": 70,
            "fractals_or_buy": 70,
            "vendor": 55,
            "trading_post": 45,
            "material": 45
        }

        effort_levels = {
            "objective_bundle": "medium",
            "achievement": "medium",
            "unlock_requirement": "medium",
            "unlock": "medium",
            "achievement_reward": "high",
            "open_world": "medium",
            "wvw_or_buy": "high",
            "fractals_or_buy": "medium",
            "vendor": "low",
            "trading_post": "low",
            "material": "low"
        }

        value = value_scores.get(
            recommendation_type,
            50
        )

        if recommendation_type == "objective":
            ideal_minutes = recommendation.get(
                "ideal_minutes",
                30
            )

            if ideal_minutes <= 15:
                effort = "low"
            elif ideal_minutes <= 45:
                effort = "medium"
            else:
                effort = "high"

        else:
            effort = effort_levels.get(
                recommendation_type,
                "medium"
            )

        progress_ratio = (
            recommendation.get(
                "progress_ratio",
                0
            )
        )

        if mode == "quick":
            score = self._quick_score(
                value=value,
                effort=effort,
                progress_ratio=progress_ratio
            )

        elif mode == "play":
            score = self._play_score(
                value=value,
                effort=effort,
                progress_ratio=progress_ratio,
                activity=recommendation["activity"]
            )

        else:
            score = self._progress_score(
                value=value,
                effort=effort,
                progress_ratio=progress_ratio
            )

        recommendation["effort"] = (
            effort
        )

        recommendation["value"] = (
            "high"
            if value >= 90
            else "medium"
            if value >= 60
            else "low"
        )

        if recommendation.get("time_gated"):
            score += 10

        score += recommendation.get(
            "score_adjustment",
            0
        )

        recommendation["score"] = round(
            score,
            1
        )

    def _progress_score(
        self,
        value: int,
        effort: str,
        progress_ratio: float
    ):
        effort_penalties = {
            "low": 0,
            "medium": 10,
            "high": 25
        }

        progress_bonus = (
            progress_ratio * 20
        )

        return (
            value
            - effort_penalties[effort]
            + progress_bonus
        )

    def _quick_score(
        self,
        value: int,
        effort: str,
        progress_ratio: float
    ):
        effort_bonus = {
            "low": 60,
            "medium": 20,
            "high": 0
        }

        progress_bonus = (
            progress_ratio * 60
        )

        value_bonus = (
            value * 0.25
        )

        return (
            effort_bonus[effort]
            + progress_bonus
            + value_bonus
        )

    def _play_score(
        self,
        value: int,
        effort: str,
        progress_ratio: float,
        activity: str
    ):
        activity_bonus = {
            "achievement": 50,
            "wvw": 45,
            "fractals": 45,
            "open_world": 45,
            "crafting": 10,
            "vendor": -20,
            "trading_post": -30,
            "acquisition": -20,
            "other": 0
        }

        effort_penalties = {
            "low": 0,
            "medium": 5,
            "high": 15
        }

        progress_bonus = (
            progress_ratio * 20
        )

        value_bonus = (
            value * 0.5
        )

        return (
            activity_bonus.get(
                activity,
                0
            )
            - effort_penalties[effort]
            + progress_bonus
            + value_bonus
        )

    def _is_directly_recommendable(
        self,
        item_id: int
    ):
        metadata = (
            self._get_acquisition_metadata(
                item_id
            )
        )

        return metadata.get(
            "recommend_directly",
            True
        )

    def _get_acquisition_metadata(
        self,
        item_id: int
    ):
        return self.acquisition.get(
            str(item_id),
            {}
        )

    def _collection_progress_ratio(
        self,
        collection: dict
    ):
        maximum = collection.get(
            "max",
            0
        )

        if maximum == 0:
            return 0

        return (
            collection.get(
                "current",
                0
            )
            / maximum
        )

    def _material_progress_ratio(
        self,
        material: dict
    ):
        required = material.get(
            "required",
            0
        )

        if required == 0:
            return 0

        return (
            material.get(
                "owned",
                0
            )
            / required
        )
