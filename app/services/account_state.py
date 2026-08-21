import asyncio
import httpx
from dataclasses import dataclass

from app.services.gw2_api import GW2Client


@dataclass
class AccountState:
    achievements: list
    achievement_by_id: dict
    item_counts: dict
    recipe_ids: set

    @classmethod
    async def load(cls, client: GW2Client | None = None):
        if client is not None:
            return await cls._load_with_client(client)

        timeout = httpx.Timeout(20.0)

        async with httpx.AsyncClient(timeout=timeout) as http_client:
            shared_client = GW2Client(http_client=http_client)
            return await cls._load_with_client(shared_client)

    @classmethod
    async def _load_with_client(cls, client: GW2Client):
        (
            achievements,
            bank,
            materials,
            shared_inventory,
            characters,
            recipes
        ) = await asyncio.gather(
            client.get_account_achievements(),
            client.get_bank(),
            client.get_materials(),
            client.get_shared_inventory(),
            client.get_characters(),
            client.get_account_recipes()
        )

        item_counts = {}

        def add_item(item):
            if item is None:
                return

            item_id = item.get("id")
            count = item.get("count", 0)

            if item_id is None:
                return

            item_counts[item_id] = (
                item_counts.get(item_id, 0)
                + count
            )

        for item in bank:
            add_item(item)

        for item in materials:
            add_item(item)

        for item in shared_inventory:
            add_item(item)

        for character in characters:
            for bag in character.get("bags", []):
                if bag is None:
                    continue

                for item in bag.get("inventory", []):
                    add_item(item)

        return cls(
            achievements=achievements,
            achievement_by_id={
                achievement["id"]: achievement
                for achievement in achievements
            },
            item_counts=item_counts,
            recipe_ids=set(recipes)
        )
