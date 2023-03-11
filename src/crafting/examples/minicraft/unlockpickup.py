"""# MiniCraft - UnlockPickup"""

import os
from typing import List

from crafting.elements import Item, Zone, ItemStack
from crafting.env import CraftingEnv
from crafting.task import GetItemTask
from crafting.transformation import Transformation
from crafting.world import world_from_transformations


class MiniCraftUnlockPickup(CraftingEnv):
    """Reproduces the minigrid
    [UnlockPickup](https://minigrid.farama.org/environments/minigrid/UnlockPickupEnv/)
    gridworld environment as a crafting environment.

    ![Minigrid UnlockPickup display](https://minigrid.farama.org/_images/UnlockPickupEnv.gif)
    """

    START = Zone("start_room")
    """Start room."""
    BOX_ROOM = Zone("box_room")
    """Room with a box inside."""

    KEY = Item("key")
    """Key used to unlock the door."""
    BOX = Item("box")
    """Box to pickup."""
    WEIGHT = Item("weight")
    """Weight of carried items, can only be less than 1."""

    OPEN_DOOR = Item("open_door")
    """Open door between the two rooms."""
    LOCKED_DOOR = Item("locked_door")
    """Locked door between the two rooms, can be unlocked with a key."""

    def __init__(self, **kwargs) -> None:
        """
        Kwargs:
            See `crafting.env.CraftingEnv`
        """
        transformations = self._build_transformations()
        world = world_from_transformations(
            transformations=transformations,
            start_zone=self.START,
        )
        self.task = GetItemTask(self.BOX)
        world.resources_path = os.path.join(os.path.dirname(__file__), "resources")
        super().__init__(
            world, purpose=self.task, name="MiniCraftUnlockPickup", **kwargs
        )

    def _build_transformations(self) -> List[Transformation]:
        transformations = []

        zones = (self.START, self.BOX_ROOM)
        items_in_zone = [(self.KEY, self.START), (self.BOX, self.BOX_ROOM)]

        for item, zone in items_in_zone:
            inventory_changes = {
                "current_zone": {"add": [item]},
                # Prevent searching if already found
                "player": {"max": [item]},
            }
            # Prevent searching if item was placed elsewhere
            inventory_changes.update(
                {zone: {"max": [item]} for zone in zones},
            )
            search_for_item = Transformation(
                inventory_changes=inventory_changes,
                zones=[zone],
            )
            transformations.append(search_for_item)

            pickup = Transformation(
                inventory_changes={
                    "player": {
                        "add": [item, self.WEIGHT],
                        # Prevent carrying more than one item
                        "max": [self.WEIGHT],
                    },
                    "current_zone": {"remove": [item]},
                },
            )
            put_down = Transformation(
                inventory_changes={
                    "player": {"remove": [item, self.WEIGHT]},
                    "current_zone": {"add": [item]},
                },
            )
            transformations += [pickup, put_down]

        search_for_door = Transformation(
            inventory_changes={
                "current_zone": {
                    "add": [self.LOCKED_DOOR],
                    "max": [self.LOCKED_DOOR, ItemStack(self.OPEN_DOOR, 0)],
                },
            },
            zones=[self.START],
        )
        transformations.append(search_for_door)

        unlock_door = Transformation(
            inventory_changes={
                "player": {
                    "remove": [self.KEY],
                    "add": [self.KEY],
                },
                "current_zone": {
                    "remove": [self.LOCKED_DOOR],
                    "add": [self.OPEN_DOOR],
                },
            },
        )
        transformations.append(unlock_door)

        move_to_box_room = Transformation(
            destination=self.BOX_ROOM,
            inventory_changes={
                "current_zone": {
                    "remove": [self.OPEN_DOOR],
                    "add": [self.OPEN_DOOR],
                },
            },
            zones=[self.START],
        )
        transformations.append(move_to_box_room)

        move_to_start_room = Transformation(
            destination=self.START,
            zones=[self.BOX_ROOM],
        )
        transformations.append(move_to_start_room)

        return transformations
