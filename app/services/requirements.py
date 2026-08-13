import json
from pathlib import Path

from app.services.account_inventory import AccountInventory


class RequirementAnalyzer:

    def __init__(self):
        self.inventory = AccountInventory()

        data_file = (
            Path(__file__).parent.parent
            / "game_data"
            / "recipes.json"
        )

        with open(data_file, "r", encoding="utf-8") as file:
            self.recipes = json.load(file)

    async def analyze_recipe(
        self,
        item_id: int,
        item_counts: dict | None = None
    ):
        if item_counts is None:
            item_counts = await self.inventory.get_item_counts()

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
                missing_materials.append({
                    "id": leaf_item_id,
                    "name": material["name"],
                    "owned": owned,
                    "required": required,
                    "missing": missing
                })

        return {
            **tree,
            "missing_materials": missing_materials
        }

    async def analyze_recipes(
        self,
        item_ids: list[int],
        item_counts: dict | None = None
    ):
        if item_counts is None:
            item_counts = await self.inventory.get_item_counts()

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
                missing_materials.append({
                    "id": leaf_item_id,
                    "name": material["name"],
                    "owned": owned,
                    "required": required,
                    "missing": missing
                })

        return missing_materials

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