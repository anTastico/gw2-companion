class TrackerService:

    def __init__(self, gw2):
        self.gw2 = gw2

    async def calculate(self, tracker):

        account = await self.gw2.get_account_achievements()

        completed = {
            achievement["id"]
            for achievement in account
            if achievement.get("done")
        }

        steps = []

        for achievement in tracker["achievements"]:

            steps.append({
                "id": achievement["id"],
                "name": achievement["name"],
                "completed": achievement["id"] in completed
            })

        total = len(steps)
        finished = sum(step["completed"] for step in steps)

        return {
            "name": tracker["name"],
            "completed": finished,
            "total": total,
            "percent": round(finished / total * 100, 1) if total else 0,
            "steps": steps
        }