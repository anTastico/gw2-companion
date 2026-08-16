import json
from pathlib import Path

from app.trackers.regalia import RegaliaTracker
from app.trackers.vision import VisionTracker
from app.trackers.aurora import AuroraTracker


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
        minutes: int | None = None
    ):
        regalia = await self.regalia.progress()
        vision = await self.vision.progress()
        aurora = await self.aurora.progress()

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
                        recommendations.append({
                            "goal": "Vision",
                            "type": "objective",
                            "title": objective["name"],
                            "collection": collection["name"],
                            "collection_progress": (
                                f"{collection['current']}/"
                                f"{collection['max']}"
                            ),
                            "progress_ratio": (
                                self._collection_progress_ratio(
                                    collection
                                )
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
                                "action",
                                (
                                    "Complete this objective "
                                    "for the collection."
                                )
                            ),
                            "reason": (
                                f"This is an incomplete objective "
                                f"for {collection['name']}."
                            )
                        })

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

    def _add_aurora_recommendations(
        self,
        aurora: dict,
        recommendations: list
    ):
        summary = aurora.get(
            "summary",
            {}
        )

        status = summary.get(
            "status"
        )

        if status == "locked":
            next_step = summary.get(
                "next_step"
            )

            if next_step:
                recommendations.append({
                    "goal": "Aurora",
                    "type": "unlock",
                    "title": (
                        f"Unlock "
                        f"{next_step['stage']}"
                    ),
                    "progress_ratio": 0,
                    "action": (
                        "Complete the prerequisite "
                        "needed to unlock this "
                        "Aurora stage."
                    ),
                    "reason": (
                        "Aurora progression is "
                        "currently locked."
                    )
                })

            return

        incomplete_collections = []

        for stage in aurora["stages"]:
            if stage["status"] == "locked":
                continue

            for collection in stage["collections"]:
                if not collection["completed"]:
                    incomplete_collections.append(
                        collection
                    )

        if incomplete_collections:
            best_collection = max(
                incomplete_collections,
                key=self._collection_progress_ratio
            )

            recommendations.append({
                "goal": "Aurora",
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
                    "incomplete Aurora collection."
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

        recommendations.append({
            "goal": "Prismatic Champion's Regalia",
            "type": "achievement",
            "title": next_step["name"],
            "progress_ratio": 0,
            "action": (
                "Complete this Return achievement."
            ),
            "reason": (
                "This is the next incomplete "
                "Regalia achievement in the "
                "tracked list."
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
            utilization_ratio = (
                ideal / minutes
                if minutes > 0
                else 1
            )

            time_adjustment = (
                30 * utilization_ratio
            )

            if utilization_ratio >= 0.6:
                label = "excellent"
            else:
                label = "good"

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
            "achievement": 100,
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
            "achievement": "medium",
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
                progress_ratio=progress_ratio,
                activity=recommendation["activity"]
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
        progress_ratio: float,
        activity: str
    ):
        effort_bonus = {
            "low": 25,
            "medium": 10,
            "high": 0
        }

        activity_bonus = {
            "open_world": 20,
            "achievement": 15,
            "fractals": 5,
            "wvw": 0,
            "crafting": 0,
            "vendor": -10,
            "trading_post": -20,
            "acquisition": -10,
            "other": 0
        }

        progress_bonus = (
            progress_ratio * 25
        )

        value_bonus = (
            value * 0.65
        )

        return (
            effort_bonus[effort]
            + activity_bonus.get(
                activity,
                0
            )
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
            progress_ratio * 12
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