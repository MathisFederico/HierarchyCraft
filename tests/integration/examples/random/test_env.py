# Crafting a gym-environment to simultate inventory managment
# Copyright (C) 2021-2022 Mathïs FEDERICO <https://www.gnu.org/licenses/>

import pytest
import pytest_check as check

from networkx import is_isomorphic

from crafting.examples.random.env import RandomCraftingEnv


class TestTasks:

    """Tasks of the MineCrafting environment"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures."""
        n_items = 10
        self.env_settings = {
            'n_items': n_items,
            'n_tools': int(0.1*n_items),
            'n_foundables': int(0.3*n_items),
            'n_required_tools': [0.25, 0.4, 0.2, 0.1, 0.05],
            'n_inputs_per_craft': [0.1, 0.6, 0.3],
        }

    def test_same_seed_same_requirements_graph(self):
        env = RandomCraftingEnv(seed=42, **self.env_settings)
        env2 = RandomCraftingEnv(seed=42, **self.env_settings)

        check.equal(env.rng_seeds, env2.rng_seeds)

        for rd_env in (env, env2):
            edges = list(rd_env.world.get_requirements_graph().edges())
            edges.sort()
            print(rd_env.rng_seeds, rd_env.np_random)
            print(edges)
            print()

        check.is_true(
            is_isomorphic(
                env.world.get_requirements_graph(),
                env2.world.get_requirements_graph(),
            )
        )

    def test_different_seed_different_requirements_graph(self):
        env = RandomCraftingEnv(seed=42, **self.env_settings)
        env2 = RandomCraftingEnv(seed=43, **self.env_settings)

        check.not_equal(env.rng_seeds, env2.rng_seeds)

        check.is_false(
            is_isomorphic(
                env.world.get_requirements_graph(),
                env2.world.get_requirements_graph(),
            )
        )