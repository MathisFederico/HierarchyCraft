# pylint: disable=no-member

""" Random Crafting Environment

Generate a random Crafting environment using basic constructor rules.

"""

from typing import Dict, List, Optional

import numpy as np

from crafting.elements import Item, Stack
from crafting.env import CraftingEnv
from crafting.transformation import Transformation
from crafting.world import world_from_transformations
from crafting.purpose import GetItemTask, Purpose


class RandomCraftingEnv(CraftingEnv):

    """Random Crafting Environment"""

    def __init__(
        self,
        n_items_per_n_inputs: Optional[Dict[int, int]] = None,
        seed: int = None,
        **kwargs,
    ):
        """Random Crafting Environment.

        Args:
            n_items_per_n_inputs: Mapping from the number of inputs to the number of items
                with this number of inputs.
        Kwargs:
            max_step: The maximum number of steps until done.
        """
        if n_items_per_n_inputs is None:
            n_items_per_n_inputs = {0: 5, 1: 5, 2: 10, 3: 5}

        self.seed = seed
        self.np_random = np.random.RandomState(seed)
        self.n_items = sum(n_items_per_n_inputs.values())
        env_characteristics = "".join(
            [
                f"{n_inputs}I{n_items}"
                for n_inputs, n_items in n_items_per_n_inputs.items()
            ]
        )
        name = f"RandomCrafing-{env_characteristics}-S{seed}"
        self.items: List[Item] = []
        transformations = self._transformations(n_items_per_n_inputs)
        world = world_from_transformations(transformations)
        if "purpose" not in kwargs:
            purpose = Purpose()
            for item in self.items:
                purpose.add_task(GetItemTask(item))
            kwargs["purpose"] = purpose
        super().__init__(world, name=name, **kwargs)

    def _transformations(
        self,
        n_items_per_n_inputs: Dict[int, int],
    ) -> List[Transformation]:
        """Build transformations for a RandomCrafting environement.

        Args:
            n_items_per_n_inputs: Mapping from the number of inputs to the number of items
                with this number of inputs.
        Returns:
            A list of random (but accessible) transformations.

        """

        for n_inputs, n_items in n_items_per_n_inputs.items():
            self.items += [Item(f"{n_inputs}_{i}") for i in range(n_items)]

        transformations = []

        # Items with 0 inputs are accessible from the start
        accessible_items = []
        for item in self.items:
            if item.name.startswith("0"):
                search_item = Transformation(
                    inventory_changes={"player": {"add": [Stack(item)]}}
                )
                transformations.append(search_item)
                accessible_items.append(item)

        # Other items are built with inputs
        unaccessible_items = [
            item for item in self.items if item not in accessible_items
        ]
        self.np_random.shuffle(unaccessible_items)

        while len(accessible_items) < len(self.items):
            new_accessible_item = unaccessible_items.pop()
            outputs = [Stack(new_accessible_item)]

            n_inputs = int(new_accessible_item.name.split("_")[0])
            n_inputs = min(n_inputs, len(accessible_items))

            # Chooses randomly accessible items and build Stacks of size 1.
            input_items = list(
                self.np_random.choice(accessible_items, size=n_inputs, replace=False)
            )
            inputs = [Stack(item) for item in input_items]

            # Build recipe
            new_recipe = Transformation(
                inventory_changes={"player": {"remove": inputs, "add": outputs}}
            )
            transformations.append(new_recipe)
            accessible_items.append(new_accessible_item)

        return transformations
