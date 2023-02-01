# Crafting a meta-environment to simultate inventory managment
# Copyright (C) 2021-2023 Mathïs FEDERICO <https://www.gnu.org/licenses/>


from crafting.task import GetItemTask
from crafting.examples.minecraft.env import MineCraftingEnv
from crafting.examples.minecraft.items import (
    COBBLESTONE,
    IRON_INGOT,
    DIAMOND,
    ENCHANTING_TABLE,
)

# gym is an optional dependency
try:
    import gym

    ENV_PATH = "crafting.examples.minecraft.env:MineCraftingEnv"

    # Simple MineCrafting with no reward, only penalty on illegal actions
    gym.register(
        id="MineCrafting-NoReward-v1",
        entry_point=ENV_PATH,
    )

    # Get COBBLESTONE
    gym.register(
        id="MineCrafting-Stone-v1",
        entry_point=ENV_PATH,
        kwargs={
            "purpose": GetItemTask(COBBLESTONE, reward=10),
        },
    )

    # Get IRON_INGOT
    gym.register(
        id="MineCrafting-Iron-v1",
        entry_point=ENV_PATH,
        kwargs={
            "purpose": GetItemTask(IRON_INGOT, reward=10),
        },
    )

    # Get DIAMOND
    gym.register(
        id="MineCrafting-Diamond-v1",
        entry_point=ENV_PATH,
        kwargs={
            "purpose": GetItemTask(DIAMOND, reward=10),
        },
    )

    # Get ENCHANTING_TABLE
    gym.register(
        id="MineCrafting-EnchantingTable-v1",
        entry_point=ENV_PATH,
        kwargs={
            "purpose": GetItemTask(ENCHANTING_TABLE, reward=10),
        },
    )


except ImportError:
    pass
