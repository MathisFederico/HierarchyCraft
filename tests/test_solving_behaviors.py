import pytest
import pytest_check as check


@pytest.mark.slow
def test_doc_example():
    from crafting.examples import MineCraftingEnv
    from crafting.examples.minecraft.items import DIAMOND
    from crafting.task import GetItemTask

    get_diamond = GetItemTask(DIAMOND)
    env = MineCraftingEnv(purpose=get_diamond)
    solving_behavior = env.solving_behavior(get_diamond)

    done = False
    observation = env.reset()
    while not done:
        action = solving_behavior(observation)
        observation, _reward, done, _info = env.step(action)

    check.is_true(get_diamond.is_terminated)  # DIAMOND has been obtained !
