from typing import List, Tuple

import numpy as np
import pytest
import pytest_check as check

from crafting.env import CraftingEnv
from crafting.purpose import Purpose, RewardShaping
from crafting.task import GetItemTask, GoToZoneTask, PlaceItemTask, Task
from crafting.transformation import Transformation
from crafting.world import Item, ItemStack, World, Zone


class TestNoPurpose:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.purpose = Purpose(None)

    def test_reward(self):
        reward = self.purpose.reward(None, None, None)
        check.equal(reward, 0)

    def test_is_terminal(self):
        check.is_false(self.purpose.is_terminal(None, None, None))


def test_time_penalty():
    purpose = Purpose(None, timestep_reward=-1)
    check.equal(purpose.reward(None, None, None), -1)


class DummyPosEqualTask(Task):
    def __init__(self, reward, goal_position) -> None:
        self.is_built = False
        self._reward = reward
        self.goal_position = goal_position

    def reward(
        self,
        player_inventory: np.ndarray,
        position: np.ndarray,
        zones_inventory: np.ndarray,
    ) -> float:
        if position == self.goal_position:
            return self._reward
        return 0.0

    def is_terminal(
        self,
        player_inventory: np.ndarray,
        position: np.ndarray,
        zones_inventory: np.ndarray,
    ) -> bool:
        return position == self.goal_position

    def build(self, world: World) -> None:
        self.is_built = True

    def __str__(self) -> str:
        return f"Task({self.goal_position})"


class TestPurposeSingleTask:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.go_to_1 = DummyPosEqualTask(reward=5, goal_position=1)
        self.purpose = Purpose(self.go_to_1)
        self.env = CraftingEnv([])

    def test_build(self):
        self.purpose.build(self.env)
        check.is_true(self.go_to_1.is_built)

    def test_reward(self):
        check.equal(self.purpose.reward(None, 0, None), 0)
        check.equal(self.purpose.reward(None, 1, None), 5)

    def test_is_terminal(self):
        check.is_false(self.purpose.is_terminal(None, 0, None))
        check.is_true(self.purpose.is_terminal(None, 1, None))


class TestPurposeMultiTasks:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.purpose = Purpose()
        self.go_to_0 = DummyPosEqualTask(reward=10, goal_position=0)
        self.purpose.add_task(self.go_to_0)
        self.go_to_1 = DummyPosEqualTask(reward=5, goal_position=1)
        self.purpose.add_task(self.go_to_1, terminal_groups=["other", "default"])
        self.go_to_2 = DummyPosEqualTask(reward=3, goal_position=2)
        self.purpose.add_task(self.go_to_2, terminal_groups="other")
        self.go_to_3 = DummyPosEqualTask(reward=1, goal_position=3)
        self.purpose.add_task(self.go_to_3, terminal_groups="")
        self.env = CraftingEnv([])

    def test_build(self):
        self.purpose.build(self.env)
        for task in [self.go_to_0, self.go_to_1]:
            check.is_true(task.is_built)

    def test_reward(self):
        check.equal(self.purpose.reward(None, -1, None), 0)
        check.equal(self.purpose.reward(None, 0, None), 10)
        check.equal(self.purpose.reward(None, 1, None), 5)
        check.equal(self.purpose.reward(None, 2, None), 3)
        check.equal(self.purpose.reward(None, 3, None), 1)

    def test_is_terminal_by_0_and_1(self):
        check.is_false(self.purpose.is_terminal(None, 0, None))  # Task 0 ends
        check.is_true(self.purpose.is_terminal(None, 1, None))  # Task 1 ends

    def test_is_terminal_by_1_and_2(self):
        check.is_false(self.purpose.is_terminal(None, 1, None))  # Task 1 ends
        check.is_true(self.purpose.is_terminal(None, 2, None))  # Task 2 ends

    def test_is_not_terminal_by_3(self):
        check.is_false(self.purpose.is_terminal(None, 3, None))  # Task 3 ends

    def test_add_task_with_default_reward_shaping(self):
        purpose = Purpose()
        purpose.add_task(self.go_to_0)
        check.equal(purpose.reward_shaping[self.go_to_0], RewardShaping.NONE)

    def test_add_task_with_specific_reward_shaping(self):
        purpose = Purpose()
        purpose.add_task(self.go_to_0, "required")
        check.equal(
            purpose.reward_shaping[self.go_to_0], RewardShaping.REQUIRED_ACHIVEMENTS
        )

    def test_str_full(self):
        check.equal(
            str(self.purpose),
            "Purpose(default:[Task(0),Task(1)], other:[Task(1),Task(2)], optional:[Task(3)])",
        )

    def test_str_without_optional(self):
        purpose = Purpose()
        purpose.add_task(self.go_to_0)
        purpose.add_task(self.go_to_1)
        purpose.add_task(self.go_to_2, terminal_groups="other")
        check.equal(
            str(purpose),
            "Purpose(default:[Task(0),Task(1)], other:[Task(2)])",
        )

    def test_str_empty(self):
        check.equal(str(Purpose()), "Purpose()")


class TestPurposeRewardShaping:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.zones = [Zone(str(i)) for i in range(5)]
        self.items = [Item(str(i)) for i in range(4)]

        go_to_zones = []
        for zone in self.zones[:4]:
            go_to_zones.append(Transformation(destination=zone))
        go_to_zones.append(
            Transformation(
                destination=self.zones[4],
                removed_player_items=[self.items[0]],
                removed_zone_items=[self.items[0]],
                removed_destination_items=[self.items[1]],
                zones=self.zones[:2],
            )
        )

        # Item 0
        search_0 = Transformation(
            added_player_items=[self.items[0]],
            zones=[self.zones[0]],
        )
        # Item 0 > Item 1
        craft_1 = Transformation(
            removed_player_items=[self.items[0]],
            added_player_items=[self.items[1]],
        )
        # Item 1 > Item 2
        craft_2 = Transformation(
            removed_player_items=[self.items[1]],
            added_player_items=[self.items[2]],
            zones=[self.zones[1]],
        )
        # Item 2 > 2 * Item 2
        craft_2_with_2 = Transformation(
            removed_player_items=[self.items[2]],
            added_player_items=[ItemStack(self.items[2], 2)],
        )
        # Item 3
        search_3 = Transformation(
            added_player_items=[self.items[3]],
            zones=[self.zones[2]],
        )

        # Zone Item 0
        place_0 = Transformation(
            removed_player_items=[self.items[0]],
            added_zone_items=[self.items[0]],
        )

        # Zone Item 2
        place_2 = Transformation(
            removed_player_items=[self.items[2]],
            removed_zone_items=[self.items[0]],
            added_zone_items=[self.items[2]],
        )

        self.get_item_2 = GetItemTask(self.items[2], reward=10.0)
        self.place_item_2_in_zone_0 = PlaceItemTask(
            item_stack=self.items[2], zones=[self.zones[3]], reward=10.0
        )
        self.go_to_4 = GoToZoneTask(self.zones[4], reward=10.0)
        self.env = CraftingEnv(
            transformations=[
                search_0,
                craft_1,
                craft_2,
                craft_2_with_2,
                search_3,
                place_0,
                place_2,
                *go_to_zones,
            ]
        )
        self.zone_items = self.env.world.zones_items

    def test_no_reward_shaping(self):
        purpose = Purpose()
        purpose.add_task(self.get_item_2, RewardShaping.NONE)
        check.equal(purpose.tasks, [self.get_item_2])

    def test_all_achievements_shaping(self):
        purpose = Purpose()
        purpose.add_task(self.get_item_2, reward_shaping=RewardShaping.ALL_ACHIVEMENTS)
        purpose.build(self.env)
        _check_get_item_tasks(self.items, purpose.tasks)
        _check_go_to_zone_tasks(self.zones, purpose.tasks)
        _check_place_item_tasks(
            [(zone_item, None) for zone_item in self.zone_items], purpose.tasks
        )

    def test_shaping_subtasks_are_optional(self):
        purpose = Purpose()
        purpose.add_task(self.get_item_2, reward_shaping=RewardShaping.ALL_ACHIVEMENTS)
        purpose.build(self.env)
        check.equal(list(purpose.terminal_groups.values()), [[self.get_item_2]])

    def test_inputs_achivements_shaping(self):
        purpose = Purpose()
        purpose.add_task(
            self.get_item_2,
            reward_shaping=RewardShaping.INPUTS_ACHIVEMENT,
        )
        purpose.build(self.env)
        _check_get_item_tasks([self.items[1]], purpose.tasks)
        _check_go_to_zone_tasks([self.zones[1]], purpose.tasks)

    def test_requires_achivements_shaping(self):
        purpose = Purpose()
        purpose.add_task(
            self.get_item_2,
            reward_shaping=RewardShaping.REQUIRED_ACHIVEMENTS,
        )
        purpose.build(self.env)
        _check_get_item_tasks(self.items[:2], purpose.tasks)
        _check_go_to_zone_tasks(self.zones[:2], purpose.tasks)

    def test_inputs_achivements_shaping_place_item(self):
        purpose = Purpose()
        purpose.add_task(
            self.place_item_2_in_zone_0,
            reward_shaping=RewardShaping.INPUTS_ACHIVEMENT,
        )
        purpose.build(self.env)
        _check_get_item_tasks([self.items[2]], purpose.tasks)
        _check_go_to_zone_tasks([self.zones[3]], purpose.tasks)
        _check_place_item_tasks([(self.items[0], None)], purpose.tasks)

    def test_requires_achivements_shaping_place_item(self):
        purpose = Purpose()
        purpose.add_task(
            self.place_item_2_in_zone_0,
            reward_shaping=RewardShaping.REQUIRED_ACHIVEMENTS,
        )
        purpose.build(self.env)
        _check_get_item_tasks(self.items[:3], purpose.tasks)
        _check_go_to_zone_tasks(self.zones[:2] + [self.zones[3]], purpose.tasks)
        _check_place_item_tasks([(self.items[0], None)], purpose.tasks)

    def test_inputs_achivements_shaping_go_to_zone(self):
        purpose = Purpose()
        purpose.add_task(
            self.go_to_4,
            reward_shaping=RewardShaping.INPUTS_ACHIVEMENT,
        )
        purpose.build(self.env)
        _check_get_item_tasks(self.items[:1], purpose.tasks)
        _check_go_to_zone_tasks(self.zones[:2], purpose.tasks)
        _check_place_item_tasks(
            [
                (self.items[0], None),
                (self.items[1], None),
            ],
            purpose.tasks,
        )

    def test_requires_achivements_shaping_go_to_zone(self):
        purpose = Purpose()
        purpose.add_task(
            self.go_to_4,
            reward_shaping=RewardShaping.REQUIRED_ACHIVEMENTS,
        )
        purpose.build(self.env)
        _check_get_item_tasks(self.items[:1], purpose.tasks)
        _check_go_to_zone_tasks(self.zones[:2], purpose.tasks)
        _check_place_item_tasks(
            [
                (self.items[0], None),
                (self.items[1], None),
            ],
            purpose.tasks,
        )


def _check_get_item_tasks(items: List[Item], tasks: List[Task]):
    all_items_stacks = [ItemStack(item) for item in items]
    expected_task_names = [
        GetItemTask.get_name(item_stack) for item_stack in all_items_stacks
    ]
    _check_in_tasks_names(tasks, expected_task_names)


def _check_go_to_zone_tasks(zones: List[Zone], tasks: List[Task]):
    expected_task_names = [GoToZoneTask.get_name(zone) for zone in zones]
    _check_in_tasks_names(tasks, expected_task_names)


def _check_place_item_tasks(
    items_and_zones: List[Tuple[Item, Zone]], tasks: List[Task]
):
    stacks_and_zones = [(ItemStack(item), zones) for item, zones in items_and_zones]
    expected_task_names = [
        PlaceItemTask.get_name(stack, zones) for stack, zones in stacks_and_zones
    ]
    _check_in_tasks_names(tasks, expected_task_names)


def _check_in_tasks_names(tasks: List[Task], expected_task_names: List[str]):
    task_names = [task.name for task in tasks]
    for task_name in expected_task_names:
        check.is_in(task_name, task_names)