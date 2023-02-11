"""# Purpose in Crafting

Crafting environments are sandbox environments and do not have a precise purpose by default.
But of course, purpose can be added in any Crafting environment by setting up one or multiple tasks.

Tasks can be one of:
* GetItemTask: Get the given item
* GoToZoneTask: Go to the given zone
* PlaceItemTask: Place the given item in the given zone (or any zone if none given).


## Single task purpose

When a single task is passed to a Crafting environment, it will automaticaly build a purpose.
Then the environment will terminates if the task is completed.

```python
from crafting import MineCraftingEnv
from crafting.purpose import GetItemTask
from crafting.examples.minecraft.items import DIAMOND

get_diamond = GetItemTask(DIAMOND, reward=10)
env = MineCraftingEnv(purpose=get_diamond)
```

## Reward shaping

Achievement tasks only rewards the player when completed. But this long term feedback is known 
to be challenging. To ease learning such tasks, Crafting Purpose can generate substasks to give 
intermediate feedback, this process is also known as reward shaping.

Reward shaping can be one of:

* "none": No reward shaping
* "all": All items and zones will be associated with an achievement subtask.
* "required": All (recursively) required items and zones for the given task will be associated with an achievement subtask.
* "inputs": Items and zones consumed by any transformation solving the task will be associated with an achievement subtask.

For example, let's add the "required" reward shaping to the get_diamond task:

```python
from crafting import MineCraftingEnv
from crafting.purpose import Purpose, GetItemTask
from crafting.examples.minecraft.items import DIAMOND

get_diamond = GetItemTask(DIAMOND, reward=10)
purpose = Purpose(shaping_value=2)
purpose.add_task(get_diamond, reward_shaping="required")

env = MineCraftingEnv(purpose=purpose)
```

Then getting the IRON_INGOT item for the first time will give a reward of 2.0 to the player, because
IRON_INGOT is used to craft the IRON_PICKAXE that is itself used to get a DIAMOND.

## Multi-tasks and terminal groups

In a sandbox environment, why limit ourselves to only one task ?
In crafting, a purpose can be composed on multiple tasks.
But then the question arise: "When does the purpose terminates ?".
When any task is done ? When all tasks are done ?

To solve this, we need to introduce terminal groups.
Terminal groups are represented with strings.

The purpose will termitate if ANY of the terminal groups have ALL its tasks done.

When adding a task to a purpose, one can choose one or multiple terminal groups like so:

```python
from crafting import MineCraftingEnv
from crafting.purpose import Purpose, GetItemTask, GoToZone
from crafting.examples.minecraft.items import DIAMOND, GOLD_INGOT, EGG
from crafting.examples.minecraft.zones import END

get_diamond = GetItemTask(DIAMOND, reward=10)
get_gold = GetItemTask(GOLD_INGOT, reward=5)
get_egg = GetItemTask(EGG, reward=100)
go_to_end = GoToZone(END, reward=20)

purpose = Purpose()
purpose.add_task(get_diamond, reward_shaping="required", terminal_groups="get rich!")
purpose.add_task(get_gold, terminal_groups=["golden end", "get rich!"])
purpose.add_task(go_to_end, reward_shaping="inputs", terminal_groups="golden end")
purpose.add_task(get_egg, terminal_groups=None)

env = MineCraftingEnv(purpose=purpose)
```

Here the environment will terminate if the player gets both diamond and gold_ingot items ("get rich!" group) 
or if the player gets a gold_ingot and reaches the end zone ("golden end" group).
The task get_egg is optional and cannot terminate the purpose anyhow, but it will still rewards the player if completed.

Just like this last task, reward shaping subtasks are always optional.

"""

from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Union

import networkx as nx
import numpy as np

from crafting.requirement_graph import ReqNodesTypes, req_node_name
from crafting.task import GetItemTask, GoToZoneTask, PlaceItemTask, Task
from crafting.world import Item, Zone

if TYPE_CHECKING:
    from crafting.env import CraftingEnv


class RewardShaping(Enum):
    NONE = "none"
    ALL_ACHIVEMENTS = "all"
    REQUIRED_ACHIVEMENTS = "required"
    INPUTS_ACHIVEMENT = "inputs"


class Purpose:
    """A purpose for a Crafting player based on a list of tasks."""

    def __init__(
        self,
        tasks: Optional[Union[Task, List[Task]]] = None,
        timestep_reward: float = 0.0,
        default_reward_shaping: RewardShaping = RewardShaping.NONE,
        shaping_value: float = 1.0,
    ) -> None:
        """A purpose for a Crafting player based on a list of tasks.

        Args:
            tasks (Union[Task, List[Task]], optional): Tasks to add to the Purpose.
                Defaults to None.
            timestep_reward (float, optional): Reward for each timestep.
                Defaults to 0.0.
            default_reward_shaping (RewardShaping, optional): Default reward shaping for tasks.
                Defaults to RewardShaping.NONE.
            shaping_value (float, optional): Reward value used in reward shaping if any.
                Defaults to 1.0.
        """
        self.tasks: List[Task] = []
        self.timestep_reward = timestep_reward
        self.shaping_value = shaping_value
        self.default_reward_shaping = default_reward_shaping

        self.task_has_ended: Dict[Task, bool] = {}
        self.reward_shaping: Dict[Task, RewardShaping] = {}
        self.terminal_groups: Dict[str, List[Task]] = {}

        if isinstance(tasks, Task):
            tasks = [tasks]
        elif tasks is None:
            tasks = []
        for task in tasks:
            self.add_task(task, reward_shaping=default_reward_shaping)

    def add_task(
        self,
        task: Task,
        reward_shaping: Optional[RewardShaping] = None,
        terminal_groups: Optional[Union[str, List[str]]] = "default",
    ):
        """Add a new task to the purpose.

        Args:
            task (Task): Task to be added to the purpose.
            reward_shaping (Optional[RewardShaping], optional): Reward shaping for this task.
                Defaults to purpose's default reward shaping.
            terminal_groups: (Optional[Union[str, List[str]]], optional): Purpose terminates
                when all the tasks of any terminal group have been done.
                If terminal groups is '' or None, task will be optional and will
                not allow to terminate the purpose at all.
                By default, tasks are added in the 'default' group and hence
                all tasks have to be done to terminate the purpose.
        """
        if reward_shaping is None:
            reward_shaping = self.default_reward_shaping
        reward_shaping = RewardShaping(reward_shaping)
        self.task_has_ended[task] = False
        if terminal_groups:
            if isinstance(terminal_groups, str):
                terminal_groups = [terminal_groups]
            for terminal_group in terminal_groups:
                if terminal_group not in self.terminal_groups:
                    self.terminal_groups[terminal_group] = []
                self.terminal_groups[terminal_group].append(task)
        self.reward_shaping[task] = reward_shaping
        self.tasks.append(task)

    def build(self, env: "CraftingEnv"):
        """
        Builds the purpose of the player based on the given world.
        """
        if not self.tasks:
            return
        # Add reward shaping subtasks
        for task in self.tasks:
            subtasks = self._add_reward_shaping_subtasks(
                task, env, self.reward_shaping[task]
            )
            for subtask in subtasks:
                self.add_task(subtask, RewardShaping.NONE, terminal_groups=None)

        # Build all tasks
        for task in self.tasks:
            task.build(env.world)

    def reward(
        self,
        player_inventory: np.ndarray,
        position: np.ndarray,
        zones_inventory: np.ndarray,
    ) -> float:
        """
        Returns the purpose reward for the given state based on tasks.
        """
        reward = self.timestep_reward
        if not self.tasks:
            return reward
        for task in self.tasks:
            reward += task.reward(player_inventory, position, zones_inventory)
        return reward

    def is_terminal(
        self,
        player_inventory: np.ndarray,
        position: np.ndarray,
        zones_inventory: np.ndarray,
    ) -> bool:
        """
        Returns True if the state is terminal for the whole purpose.
        """
        if not self.tasks:
            return False
        for task in self.tasks:
            if not self.task_has_ended[task] and task.is_terminal(
                player_inventory, position, zones_inventory
            ):
                self.task_has_ended[task] = True
        for _terminal_group, group_tasks in self.terminal_groups.items():
            group_has_ended = all(self.task_has_ended[task] for task in group_tasks)
            if group_has_ended:
                return True
        return False

    @property
    def optional_tasks(self) -> List[Task]:
        """List of tasks in no terminal group at all."""
        terminal_tasks = []
        for term_tasks in self.terminal_groups.values():
            terminal_tasks += term_tasks
        return [task for task in self.tasks if task not in terminal_tasks]

    def _add_reward_shaping_subtasks(
        self, task: Task, env: "CraftingEnv", reward_shaping: RewardShaping
    ) -> List[Task]:
        if reward_shaping == RewardShaping.NONE:
            return []
        if reward_shaping == RewardShaping.ALL_ACHIVEMENTS:
            return _all_subtasks(env, self.shaping_value)
        if reward_shaping == RewardShaping.INPUTS_ACHIVEMENT:
            return _inputs_subtasks(task, env, self.shaping_value)
        if reward_shaping == RewardShaping.REQUIRED_ACHIVEMENTS:
            return _required_subtasks(task, env, self.shaping_value)
        raise NotImplementedError

    def __str__(self) -> str:
        terminal_groups_str = []
        for terminal_group, tasks in self.terminal_groups.items():
            tasks_str_joined = self._tasks_str(tasks)
            group_str = f"{terminal_group}:[{tasks_str_joined}]"
            terminal_groups_str.append(group_str)
        optional_tasks_str = self._tasks_str(self.optional_tasks)
        if optional_tasks_str:
            group_str = f"optional:[{optional_tasks_str}]"
            terminal_groups_str.append(group_str)
        joined_groups_str = ", ".join(terminal_groups_str)
        return f"Purpose({joined_groups_str})"

    def _tasks_str(self, tasks: List[Task]) -> str:
        tasks_str = []
        for task in tasks:
            shaping = self.reward_shaping[task]
            shaping_str = f"#{shaping.value}" if shaping != RewardShaping.NONE else ""
            tasks_str.append(f"{task}{shaping_str}")
        return ",".join(tasks_str)


def _all_subtasks(env: "CraftingEnv", shaping_reward: float) -> List[Task]:
    return _build_reward_shaping_subtasks(
        env.world.items, env.world.zones, env.world.zones_items, shaping_reward
    )


def _required_subtasks(
    task: Task, env: "CraftingEnv", shaping_reward: float
) -> List[Task]:
    relevant_items = set()
    relevant_zones = set()
    relevant_zone_items = set()

    if isinstance(task, GetItemTask):
        goal_item = task.item_stack.item
        goal_requirement_nodes = [req_node_name(goal_item, ReqNodesTypes.ITEM)]
    elif isinstance(task, PlaceItemTask):
        goal_item = task.item_stack.item
        goal_requirement_nodes = [req_node_name(goal_item, ReqNodesTypes.ZONE_ITEM)]
        goal_zones = task.zones if task.zones else []
        for zone in goal_zones:
            relevant_zones.add(zone)
            goal_requirement_nodes.append(req_node_name(zone, ReqNodesTypes.ZONE))
    elif isinstance(task, GoToZoneTask):
        goal_requirement_nodes = [req_node_name(task.zone, ReqNodesTypes.ZONE)]
    else:
        raise NotImplementedError(
            f"Unsupported reward shaping {RewardShaping.REQUIRED_ACHIVEMENTS}"
            f"for given task type: {type(task)} of {task}"
        )

    for requirement_node in goal_requirement_nodes:
        for ancestor in nx.ancestors(env.requirements_graph, requirement_node):
            ancestor_node = env.requirements_graph.nodes[ancestor]
            item_or_zone: Union[Item, Zone] = ancestor_node["obj"]
            ancestor_type = ReqNodesTypes(ancestor_node["type"])
            if ancestor_type is ReqNodesTypes.ITEM:
                relevant_items.add(item_or_zone)
            if ancestor_type is ReqNodesTypes.ZONE:
                relevant_zones.add(item_or_zone)
            if ancestor_type is ReqNodesTypes.ZONE_ITEM:
                relevant_zone_items.add(item_or_zone)
    return _build_reward_shaping_subtasks(
        relevant_items,
        relevant_zones,
        relevant_zone_items,
        shaping_reward,
    )


def _inputs_subtasks(
    task: Task, env: "CraftingEnv", shaping_reward: float
) -> List[Task]:
    relevant_items = set()
    relevant_zones = set()
    relevant_zone_items = set()

    goal_zones = []
    goal_item = None
    goal_zone_item = None
    if isinstance(task, GetItemTask):
        goal_item = task.item_stack.item
    elif isinstance(task, GoToZoneTask):
        goal_zones = [task.zone]
    elif isinstance(task, PlaceItemTask):
        goal_zone_item = task.item_stack.item
        if task.zones:
            goal_zones = task.zones
            relevant_zones |= set(task.zones)
    else:
        raise NotImplementedError(
            f"Unsupported reward shaping {RewardShaping.INPUTS_ACHIVEMENT}"
            f"for given task type: {type(task)} of {task}"
        )
    transfo_giving_item = [
        transfo
        for transfo in env.transformations
        if goal_item in transfo.produced_items
        and goal_item not in transfo.consumed_items
    ]
    transfo_placing_zone_item = [
        transfo
        for transfo in env.transformations
        if goal_zone_item in transfo.produced_zones_items
        and goal_zone_item not in transfo.consumed_zones_items
    ]
    transfo_going_to_any_zones = [
        transfo
        for transfo in env.transformations
        if transfo.destination is not None and transfo.destination in goal_zones
    ]
    relevant_transformations = (
        transfo_giving_item + transfo_placing_zone_item + transfo_going_to_any_zones
    )

    for transfo in relevant_transformations:
        relevant_items |= set(transfo.consumed_items)
        relevant_zone_items |= set(transfo.consumed_zones_items)
        if transfo.zones:
            relevant_zones |= set(transfo.zones)

    return _build_reward_shaping_subtasks(
        relevant_items,
        relevant_zones,
        relevant_zone_items,
        shaping_reward,
    )


def _build_reward_shaping_subtasks(
    items: Optional[Union[List[Item], Set[Item]]] = None,
    zones: Optional[Union[List[Zone], Set[Zone]]] = None,
    zone_items: Optional[Union[List[Item], Set[Item]]] = None,
    shaping_reward: float = 1.0,
) -> List[Task]:
    subtasks = []
    if items:
        subtasks += [GetItemTask(item, reward=shaping_reward) for item in items]
    if zones:
        subtasks += [GoToZoneTask(zone, reward=shaping_reward) for zone in zones]
    if zone_items:
        subtasks += [PlaceItemTask(item, reward=shaping_reward) for item in zone_items]
    return subtasks