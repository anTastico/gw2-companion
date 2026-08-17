from app.trackers.base import BaseTracker


class RegaliaTracker(BaseTracker):

    def __init__(self):
        super().__init__(
            name="Prismatic Champion's Regalia",
            data_filename="regalia.json"
        )

    async def progress(self):
        result = await super().progress()

        account_achievements = await self.client.get_account_achievements()
        account_progress = {
            achievement["id"]: achievement
            for achievement in account_achievements
        }

        required_by_id = {
            achievement["id"]: achievement
            for achievement in self.required
        }

        end_conjecture = required_by_id.get(5960)

        if (
            end_conjecture
            and not account_progress.get(5960, {}).get("done", False)
        ):
            chain = end_conjecture.get("dependency_chain", [])
            resolved_chain = []
            next_step = None

            for achievement in chain:
                progress = account_progress.get(achievement["id"], {})
                completed = progress.get("done", False)

                resolved = {
                    **achievement,
                    "completed": completed,
                    "account_visible": achievement["id"] in account_progress
                }
                resolved_chain.append(resolved)

                if next_step is None and not completed:
                    next_step = resolved

            if next_step:
                result["dependency"] = {
                    "target_id": 5960,
                    "target_name": "End Conjecture",
                    "next_step": next_step,
                    "chain": resolved_chain
                }

        return result
