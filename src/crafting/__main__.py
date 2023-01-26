from crafting.world import Zone, Item, ItemStack
from crafting.transformation import Transformation
from crafting.env import CraftingEnv
from crafting.render.human import render_env_with_human

start_zone = Zone("start")
other_zone = Zone("other_zone")
zones = [start_zone, other_zone]

move_to_other_zone = Transformation(
    destination=other_zone,
    zones=[start_zone],
)

wood = Item("wood")
search_wood = Transformation(
    added_player_items=[ItemStack(wood)],
)

stone = Item("stone")
search_stone = Transformation(
    added_player_items=[ItemStack(stone, 1)],
)

plank = Item("plank")
craft_plank = Transformation(
    removed_player_items=[ItemStack(wood, 1)],
    added_player_items=[ItemStack(plank, 4)],
)

table = Item("table")
craft_table = Transformation(
    removed_player_items=[ItemStack(plank, 4)],
    added_zone_items=[ItemStack(table)],
)

wood_house = Item("wood house")
build_house = Transformation(
    removed_player_items=[ItemStack(plank, 32), ItemStack(wood, 8)],
    added_zone_items=[ItemStack(wood_house)],
)

items = [wood, stone, plank]
zones_items = [table, wood_house]
transformations = [
    move_to_other_zone,
    search_wood,
    search_stone,
    craft_plank,
    craft_table,
    build_house,
]


if __name__ == "__main__":
    env = CraftingEnv(transformations, start_zone)
    render_env_with_human(env)
