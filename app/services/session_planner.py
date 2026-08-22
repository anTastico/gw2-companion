from app.services.recommendations import RecommendationService


class SessionPlanner:

    LOW_VALUE_ACTIVITIES = {
        "vendor",
        "trading_post",
        "acquisition"
    }

    LOCATION_BONUS = 20
    LOCATION_SECOND_BONUS = 10
    LOCATION_LATE_BONUS = 0
    MAP_SWITCH_PENALTY = 18
    MAP_SWITCH_PENALTY_AFTER_BLOCK = 8
    MAP_BLOCK_MINUTES = 45
    NEW_GOAL_BONUS = 10
    LOW_VALUE_PENALTY = 25
    MIN_WORTHWHILE_SCORE = 70
    MIN_MAP_SWITCH_IDEAL_RATIO = 0.75
    TIME_GATED_PLANNER_BONUS = 20
    OPENING_TIME_GATED_BONUS = 12
    DEPENDENCY_BLOCKER_BONUS = 12
    DEPENDENCY_READY_BONUS = 60
    SHARED_MATERIAL_BONUS = 15
    META_DEPENDENCY_BONUS = 12
    OPTION_PRIORITY_MAX_BONUS = 8
    OPTION_PROGRESS_MAX_BONUS = 6

    def __init__(self):
        self.recommendations = RecommendationService()

    async def build_plan(
        self,
        minutes: int,
        goal: str | None = None,
        activity: str | None = None
    ):
        result = await self.recommendations.get_recommendations(
            mode="play",
            goal=goal,
            activity=activity,
            minutes=minutes,
            full_candidate_pool=True
        )

        candidates = [
            dict(recommendation)
            for recommendation in result.get(
                "recommendations",
                []
            )
        ]

        if not candidates:
            return {
                "minutes": minutes,
                "filters": {
                    "goal": goal,
                    "activity": activity
                },
                "match_found": False,
                "message": (
                    "No recommendations fit this "
                    "session plan."
                ),
                "allocated_minutes": 0,
                "remaining_minutes": minutes,
                "location": None,
                "locations": [],
                "steps": []
            }

        steps = []
        remaining_minutes = minutes
        current_location = None
        current_location_minutes = 0
        current_location_steps = 0
        used_low_value_activity = False
        used_goals = set()
        selected_dependency_counts = {}

        while candidates:
            eligible = [
                candidate
                for candidate in candidates
                if (
                    candidate["minimum_minutes"]
                    <= remaining_minutes
                    and self._map_switch_is_worthwhile(
                        candidate=candidate,
                        remaining_minutes=remaining_minutes,
                        current_location=current_location
                    )
                    and self._dependency_option_slot_available(
                        candidate=candidate,
                        selected_dependency_counts=(
                            selected_dependency_counts
                        )
                    )
                )
            ]

            if not eligible:
                break

            scored = [
                (
                    self._planner_score(
                        candidate=candidate,
                        remaining_minutes=remaining_minutes,
                        current_location=current_location,
                        current_location_minutes=(
                            current_location_minutes
                        ),
                        current_location_steps=(
                            current_location_steps
                        ),
                        used_low_value_activity=(
                            used_low_value_activity
                        ),
                        used_goals=used_goals,
                        selected_dependency_counts=(
                            selected_dependency_counts
                        ),
                        opening_step=not steps,
                        unrestricted_goal=(
                            goal is None
                        )
                    ),
                    candidate
                )
                for candidate in eligible
            ]

            scored.sort(
                key=lambda item: (
                    item[0],
                    item[1]["score"]
                ),
                reverse=True
            )

            planner_score, best = scored[0]

            if (
                steps
                and planner_score
                < self.MIN_WORTHWHILE_SCORE
            ):
                break

            allocated_minutes = self._allocated_minutes(
                recommendation=best,
                remaining_minutes=remaining_minutes
            )

            step = {
                "order": len(steps) + 1,
                "goal": best["goal"],
                "type": best["type"],
                "title": best["title"],
                "score": best["score"],
                "planner_score": round(planner_score, 1),
                "activity": best["activity"],
                "location": best.get(
                    "location"
                ),
                "allocated_minutes": allocated_minutes,
                "minimum_minutes": best[
                    "minimum_minutes"
                ],
                "ideal_minutes": best[
                    "ideal_minutes"
                ],
                "action": best["action"],
                "reason": self._plan_reason(
                    recommendation=best,
                    current_location=current_location,
                    used_goals=used_goals,
                    unrestricted_goal=(
                        goal is None
                    )
                )
            }

            if "collection" in best:
                step["collection"] = best[
                    "collection"
                ]

            if "collection_progress" in best:
                step["collection_progress"] = best[
                    "collection_progress"
                ]

            if "progress" in best:
                step["progress"] = best[
                    "progress"
                ]

            if "time_gated" in best:
                step["time_gated"] = best["time_gated"]

            if best.get("time_gate"):
                step["time_gate"] = best["time_gate"]

            if "parent_objective" in best:
                step["parent_objective"] = best["parent_objective"]

            step["map"] = self._map_key(
                best.get("location")
            )

            if "event_dependent" in best:
                step["event_dependent"] = best[
                    "event_dependent"
                ]

            if "material_item_id" in best:
                step["material_item_id"] = best["material_item_id"]

            if "material_required" in best:
                step["material_required"] = best["material_required"]

            if "material_owned" in best:
                step["material_owned"] = best["material_owned"]

            if "material_missing" in best:
                step["material_missing"] = best["material_missing"]

            if "material_sources" in best:
                step["material_sources"] = best["material_sources"]

            if "dependency" in best:
                step["dependency"] = best[
                    "dependency"
                ]

                focus = self._dependency_focus(
                    recommendation=best,
                    current_location=best.get(
                        "location"
                    )
                )

                if focus:
                    step["focus"] = self._group_dependency_focus(
                        focus
                    )

            steps.append(
                step
            )

            remaining_minutes -= allocated_minutes

            location = self._map_key(
                best.get("location")
            )

            if location:
                if location == current_location:
                    current_location_minutes += allocated_minutes
                    current_location_steps += 1
                else:
                    current_location = location
                    current_location_minutes = allocated_minutes
                    current_location_steps = 1

            used_goals.add(
                best["goal"]
            )

            dependency = best.get("dependency") or {}
            if (
                dependency.get("tracking")
                == "achievement_options"
                and best.get("dependency_option")
            ):
                dependency_key = (
                    dependency.get("achievement_id")
                    or dependency.get("name")
                )
                selected_dependency_counts[
                    dependency_key
                ] = (
                    selected_dependency_counts.get(
                        dependency_key,
                        0
                    )
                    + 1
                )

            if (
                best["activity"]
                in self.LOW_VALUE_ACTIVITIES
            ):
                used_low_value_activity = True

            candidates.remove(
                best
            )

        allocated_minutes = (
            minutes - remaining_minutes
        )

        locations = []

        for step in steps:
            location = step.get(
                "location"
            )

            if (
                location
                and location not in locations
            ):
                locations.append(
                    location
                )

        return {
            "minutes": minutes,
            "filters": {
                "goal": goal,
                "activity": activity
            },
            "match_found": bool(steps),
            "allocated_minutes": allocated_minutes,
            "remaining_minutes": remaining_minutes,
            "location": (
                locations[0]
                if len(locations) == 1
                else None
            ),
            "locations": locations,
            "steps": steps
        }

    def _dependency_focus(
        self,
        recommendation: dict,
        current_location: str | None
    ):
        dependency = recommendation.get(
            "dependency",
            {}
        )

        focus = []

        for objective in dependency.get(
            "missing_objectives",
            []
        ):
            if not isinstance(
                objective,
                dict
            ):
                continue

            location = objective.get(
                "location"
            )

            if (
                current_location
                and location
                and location != current_location
            ):
                continue

            if not objective.get(
                "bundle"
            ):
                continue

            focus.append({
                "name": objective["name"],
                "activity": objective.get(
                    "activity"
                ),
                "location": location,
                "minimum_minutes": objective.get(
                    "minimum_minutes"
                ),
                "ideal_minutes": objective.get(
                    "ideal_minutes"
                ),
                "action": objective.get(
                    "action"
                ),
                "bundle": objective.get(
                    "bundle"
                ),
                "focus_type": objective.get(
                    "focus_type",
                    "active"
                )
            })

        return focus

    def _group_dependency_focus(
        self,
        focus: list
    ):
        groups = {
            "quick": [],
            "active": [],
            "opportunistic": []
        }

        for item in focus:
            focus_type = item.get(
                "focus_type",
                "active"
            )

            if focus_type not in groups:
                focus_type = "active"

            groups[focus_type].append(
                item
            )

        return {
            key: items
            for key, items in groups.items()
            if items
        }

    def _map_key(
        self,
        location: str | None
    ):
        if not location:
            return None

        if "," in location:
            return location.rsplit(",", 1)[-1].strip()

        return location.strip()

    def _dependency_option_slot_available(
        self,
        candidate: dict,
        selected_dependency_counts: dict
    ):
        dependency = candidate.get("dependency") or {}

        if (
            dependency.get("tracking")
            != "achievement_options"
            or not candidate.get("dependency_option")
        ):
            return True

        dependency_key = (
            dependency.get("achievement_id")
            or dependency.get("name")
        )

        remaining_required = dependency.get(
            "remaining_required",
            0
        )

        return (
            selected_dependency_counts.get(
                dependency_key,
                0
            )
            < remaining_required
        )

    def _map_switch_is_worthwhile(
        self,
        candidate: dict,
        remaining_minutes: int,
        current_location: str | None
    ):
        location = self._map_key(
            candidate.get("location")
        )

        if (
            not current_location
            or not location
            or location == current_location
        ):
            return True

        ideal = candidate[
            "ideal_minutes"
        ]

        if ideal <= 0:
            return True

        allocatable_minutes = min(
            ideal,
            remaining_minutes
        )

        ideal_ratio = (
            allocatable_minutes / ideal
        )

        return (
            ideal_ratio
            >= self.MIN_MAP_SWITCH_IDEAL_RATIO
        )

    def _planner_score(
        self,
        candidate: dict,
        remaining_minutes: int,
        current_location: str | None,
        current_location_minutes: int,
        current_location_steps: int,
        used_low_value_activity: bool,
        used_goals: set,
        selected_dependency_counts: dict,
        opening_step: bool,
        unrestricted_goal: bool
    ):
        score = candidate["score"]

        if candidate.get("time_gated"):
            score += self.TIME_GATED_PLANNER_BONUS

            if opening_step:
                score += self.OPENING_TIME_GATED_BONUS

        dependency = candidate.get("dependency") or {}
        blocker = dependency.get("primary_blocker") or {}

        if blocker:
            score += self.DEPENDENCY_BLOCKER_BONUS

            blocker_clearable_now = any((
                dependency.get("ready_to_acquire") is True,
                dependency.get("can_acquire_now") is True,
                dependency.get("ready_to_craft") is True
            ))

            if blocker_clearable_now:
                score += self.DEPENDENCY_READY_BONUS

        if (
            dependency.get("tracking")
            == "achievement_options"
            and candidate.get("dependency_option")
        ):
            dependency_key = (
                dependency.get("achievement_id")
                or dependency.get("name")
            )
            selected_count = (
                selected_dependency_counts.get(
                    dependency_key,
                    0
                )
            )
            remaining_required = dependency.get(
                "remaining_required",
                0
            )

            if selected_count < remaining_required:
                score += self.META_DEPENDENCY_BONUS

                dependency_option = (
                    candidate.get("dependency_option")
                    or {}
                )
                option_priority = dependency_option.get(
                    "priority"
                )
                if option_priority is not None:
                    # Lower numeric priority means a better option.
                    # Cap the effect so data priority guides rather
                    # than dictates the whole session.
                    priority_bonus = max(
                        0,
                        self.OPTION_PRIORITY_MAX_BONUS
                        - ((option_priority - 10) / 5)
                    )
                    score += min(
                        self.OPTION_PRIORITY_MAX_BONUS,
                        priority_bonus
                    )

                option_progress_ratio = candidate.get(
                    "option_progress_ratio"
                )
                if option_progress_ratio is not None:
                    score += (
                        option_progress_ratio
                        * self.OPTION_PROGRESS_MAX_BONUS
                    )

        material_sources = candidate.get(
            "material_sources",
            []
        )

        if len(material_sources) > 1:
            score += self.SHARED_MATERIAL_BONUS * min(
                len(material_sources) - 1,
                3
            )

        location = self._map_key(
            candidate.get("location")
        )

        if current_location:
            if location == current_location:
                if current_location_steps <= 1:
                    score += self.LOCATION_BONUS
                elif current_location_steps == 2:
                    score += self.LOCATION_SECOND_BONUS
                else:
                    score += self.LOCATION_LATE_BONUS

            elif location:
                if current_location_minutes >= self.MAP_BLOCK_MINUTES:
                    score -= self.MAP_SWITCH_PENALTY_AFTER_BLOCK
                else:
                    score -= self.MAP_SWITCH_PENALTY

        if (
            unrestricted_goal
            and used_goals
            and candidate["goal"]
            not in used_goals
        ):
            score += self.NEW_GOAL_BONUS

        if (
            used_low_value_activity
            and candidate["activity"]
            in self.LOW_VALUE_ACTIVITIES
        ):
            score -= self.LOW_VALUE_PENALTY

        ideal = candidate[
            "ideal_minutes"
        ]

        if ideal <= remaining_minutes:
            utilization = (
                ideal / remaining_minutes
            )

            score += utilization * 15

        else:
            minimum = candidate[
                "minimum_minutes"
            ]

            usable_range = max(
                ideal - minimum,
                1
            )

            progress_into_range = (
                remaining_minutes - minimum
            )

            fit_ratio = max(
                0,
                min(
                    progress_into_range
                    / usable_range,
                    1
                )
            )

            score += 5 + (fit_ratio * 10)

        return score

    def _allocated_minutes(
        self,
        recommendation: dict,
        remaining_minutes: int
    ):
        ideal = recommendation[
            "ideal_minutes"
        ]

        minimum = recommendation[
            "minimum_minutes"
        ]

        if ideal <= remaining_minutes:
            return ideal

        if minimum <= remaining_minutes:
            return remaining_minutes

        return 0

    def _plan_reason(
        self,
        recommendation: dict,
        current_location: str | None,
        used_goals: set,
        unrestricted_goal: bool
    ):
        reasons = [
            recommendation["reason"]
        ]

        material_sources = recommendation.get(
            "material_sources",
            []
        )

        if len(material_sources) > 1:
            reasons.append(
                "This material advances "
                + str(len(material_sources))
                + " Vision requirements at once."
            )

        dependency = recommendation.get(
            "dependency"
        ) or {}

        if dependency.get("primary_blocker"):
            reasons.append(
                "It also clears the current blocker for "
                + dependency.get("name", "this dependency")
                + "."
            )

        location = self._map_key(
            recommendation.get("location")
        )

        if (
            current_location
            and location == current_location
        ):
            reasons.append(
                "It also keeps you in "
                + current_location
                + "."
            )

        if (
            unrestricted_goal
            and used_goals
            and recommendation["goal"]
            not in used_goals
        ):
            reasons.append(
                "It also adds progress toward "
                + recommendation["goal"]
                + " during this session."
            )

        return " ".join(
            reasons
        )