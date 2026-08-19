from app.services.recommendations import RecommendationService


class SessionPlanner:

    LOW_VALUE_ACTIVITIES = {
        "vendor",
        "trading_post",
        "acquisition"
    }

    LOCATION_BONUS = 20
    MAP_SWITCH_PENALTY = 18
    NEW_GOAL_BONUS = 10
    LOW_VALUE_PENALTY = 25
    MIN_WORTHWHILE_SCORE = 70
    MIN_MAP_SWITCH_IDEAL_RATIO = 0.75
    TIME_GATED_PLANNER_BONUS = 20

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
        used_low_value_activity = False
        used_goals = set()

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
                        used_low_value_activity=(
                            used_low_value_activity
                        ),
                        used_goals=used_goals,
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

            location = best.get(
                "location"
            )

            if location:
                current_location = location

            used_goals.add(
                best["goal"]
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

    def _map_switch_is_worthwhile(
        self,
        candidate: dict,
        remaining_minutes: int,
        current_location: str | None
    ):
        location = candidate.get(
            "location"
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
        used_low_value_activity: bool,
        used_goals: set,
        unrestricted_goal: bool
    ):
        score = candidate["score"]

        if candidate.get("time_gated"):
            score += self.TIME_GATED_PLANNER_BONUS

        location = candidate.get(
            "location"
        )

        if current_location:
            if location == current_location:
                score += self.LOCATION_BONUS

            elif location:
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

        location = recommendation.get(
            "location"
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