import json
from pathlib import Path

from app.services.account_inventory import AccountInventory
from app.services.gw2_api import GW2Client


class RequirementAnalyzer:

    def __init__(self):
        self.inventory = AccountInventory()
        self.client = GW2Client()

        data_file = (
            Path(__file__).parent.parent
            / "game_data"
            / "recipes.json"
        )

        with open(data_file, "r", encoding="utf-8") as file:
            self.recipes = json.load(file)

        acquisition_file = (
            Path(__file__).parent.parent
            / "game_data"
            / "acquisitions.json"
        )

        with open(acquisition_file, "r", encoding="utf-8") as file:
            self.acquisitions = json.load(file)

    async def _get_wallet_counts(self):
        wallet = await self.client.get_account_wallet()

        return {
            currency["id"]: currency.get("value", 0)
            for currency in wallet
        }

    async def analyze_recipe(
        self,
        item_id: int,
        item_counts: dict | None = None,
        wallet_counts: dict | None = None
    ):
        if item_counts is None:
            item_counts = await self.inventory.get_item_counts()

        if wallet_counts is None:
            wallet_counts = await self._get_wallet_counts()

        tree = self._analyze_item(
            item_id=item_id,
            required=1,
            item_counts=item_counts
        )

        leaf_requirements = {}

        self._collect_leaf_requirements(
            node=tree,
            leaf_requirements=leaf_requirements
        )

        missing_materials = []

        for leaf_item_id, material in leaf_requirements.items():
            owned = item_counts.get(leaf_item_id, 0)
            required = material["required"]
            missing = max(required - owned, 0)

            if missing > 0:
                missing_material = {
                    "id": leaf_item_id,
                    "name": material["name"],
                    "owned": owned,
                    "required": required,
                    "missing": missing
                }

                acquisition_options = self._acquisition_options(
                    item_id=leaf_item_id,
                    units_needed=missing,
                    item_counts=item_counts,
                    wallet_counts=wallet_counts
                )

                if acquisition_options:
                    missing_material["acquisition_options"] = acquisition_options

                missing_materials.append(missing_material)

        return {
            **tree,
            "missing_materials": missing_materials
        }

    async def analyze_recipes(
        self,
        item_ids: list[int],
        item_counts: dict | None = None,
        wallet_counts: dict | None = None
    ):
        if item_counts is None:
            item_counts = await self.inventory.get_item_counts()

        if wallet_counts is None:
            wallet_counts = await self._get_wallet_counts()

        combined_requirements = {}

        for item_id in item_ids:
            tree = self._analyze_item(
                item_id=item_id,
                required=1,
                item_counts=item_counts
            )

            self._collect_leaf_requirements(
                node=tree,
                leaf_requirements=combined_requirements
            )

        missing_materials = []

        for leaf_item_id, material in combined_requirements.items():
            owned = item_counts.get(leaf_item_id, 0)
            required = material["required"]
            missing = max(required - owned, 0)

            if missing > 0:
                missing_material = {
                    "id": leaf_item_id,
                    "name": material["name"],
                    "owned": owned,
                    "required": required,
                    "missing": missing
                }

                acquisition_options = self._acquisition_options(
                    item_id=leaf_item_id,
                    units_needed=missing,
                    item_counts=item_counts,
                    wallet_counts=wallet_counts
                )

                if acquisition_options:
                    missing_material["acquisition_options"] = acquisition_options

                missing_materials.append(missing_material)

        return missing_materials

    def _acquisition_options(
        self,
        item_id: int,
        units_needed: int,
        item_counts: dict,
        wallet_counts: dict
    ):
        acquisition = self.acquisitions.get(str(item_id))

        if acquisition is None or units_needed <= 0:
            return []

        options = []

        for option in acquisition.get("options", []):
            costs = []

            for cost in option.get("costs", []):
                required = cost["amount"] * units_needed

                if cost["kind"] == "currency":
                    owned = wallet_counts.get(cost["id"], 0)
                else:
                    owned = item_counts.get(cost["id"], 0)

                missing = max(required - owned, 0)

                cost_result = {
                    "kind": cost["kind"],
                    "id": cost["id"],
                    "name": cost["name"],
                    "owned": owned,
                    "required": required,
                    "missing": missing
                }

                if cost.get("display"):
                    cost_result["display"] = cost["display"]

                costs.append(cost_result)

            options.append({
                "name": option["name"],
                "vendor": option.get("vendor"),
                "location": option.get("location"),
                "daily_limit": option.get("daily_limit"),
                "units_needed": units_needed,
                "can_afford": all(cost["missing"] == 0 for cost in costs),
                "costs": costs
            })

        return options

    def _analyze_item(
        self,
        item_id: int,
        required: int,
        item_counts: dict
    ):
        recipe = self.recipes.get(str(item_id))
        owned = item_counts.get(item_id, 0)
        missing = max(required - owned, 0)

        result = {
            "id": item_id,
            "owned": owned,
            "required": required,
            "missing": missing,
            "completed": missing == 0
        }

        if recipe is None:
            return result

        result["name"] = recipe["name"]

        if missing == 0:
            result["ingredients"] = []
            return result

        ingredients = []

        for ingredient in recipe["ingredients"]:
            child_required = ingredient["required"] * missing

            child = self._analyze_item(
                item_id=ingredient["id"],
                required=child_required,
                item_counts=item_counts
            )

            child.setdefault("name", ingredient["name"])
            ingredients.append(child)

        result["ingredients"] = ingredients

        return result

    def _collect_leaf_requirements(
        self,
        node: dict,
        leaf_requirements: dict
    ):
        ingredients = node.get("ingredients")

        if not ingredients:
            item_id = node["id"]

            if item_id not in leaf_requirements:
                leaf_requirements[item_id] = {
                    "name": node.get(
                        "name",
                        f"Item {item_id}"
                    ),
                    "required": 0
                }

            leaf_requirements[item_id]["required"] += node["required"]
            return

        for ingredient in ingredients:
            self._collect_leaf_requirements(
                node=ingredient,
                leaf_requirements=leaf_requirements
            )