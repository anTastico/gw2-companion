from collections import defaultdict

from app.services.gw2_api import GW2Client


class AccountInventory:

    def __init__(self):
        self.client = GW2Client()

    def _add_item(self, counts, item):
        if item is not None:
            counts[item["id"]] += item["count"]

    async def get_item_counts(self):
        counts = defaultdict(int)

        bank = await self.client.get_bank()
        materials = await self.client.get_materials()
        shared_inventory = await self.client.get_shared_inventory()
        characters = await self.client.get_characters()

        # Bank
        for item in bank:
            self._add_item(counts, item)

        # Material storage
        for item in materials:
            self._add_item(counts, item)

        # Shared inventory slots
        for item in shared_inventory:
            self._add_item(counts, item)

        # Character inventories
        for character in characters:
            for bag in character.get("bags", []):
                if bag is None:
                    continue

                for item in bag.get("inventory", []):
                    self._add_item(counts, item)

        return dict(counts)

    async def get_item_count(self, item_id: int):
        counts = await self.get_item_counts()

        return counts.get(item_id, 0)