# Crafting a gym-environment to simultate inventory managment
# Copyright (C) 2021 Mathïs FEDERICO <https://www.gnu.org/licenses/>

""" Rendering of the Crafting environments """

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Dict, List, Any, Union

import numpy as np
import pygame, pygame_menu
from pygame.time import Clock
from pygame.event import Event
from pygame_menu.menu import Menu

if TYPE_CHECKING:
    from crafting.env import CraftingEnv
    from crafting.world.world import World
from crafting.render.widgets import EnvWidget, InventoryWidget,ScoreWidget, \
    ZoneWidget, StepLeftWidget


def get_human_action(env:CraftingEnv, additional_events:List[Event]=None, 
        can_be_none:bool=False, **kwargs):
    """ Update the environment rendering and gather potential action given by the UI.

    Args:
        env: The running Crafting environment.
        additional_events (Optional): Additional simulated pygame events.
        can_be_none: If False, this function will loop on rendering until an action is found.
            If True, will return None if no action was found after one rendering update.

    Returns:
        The action found using the UI.

    """
    action_chosen = False
    while not action_chosen:
        action = update_rendering(env, additional_events=additional_events, **kwargs)
        action_chosen = action is not None or can_be_none
    return action

def create_window(env: CraftingEnv) -> Dict[str, Any]:
    """ Initialise pygame window, menus and widgets for the UI.

    Args:
        env: The running Crafting environment.

    Returns:
        Dictionary of rendering variables.

    """
    os.environ['SDL_VIDEO_CENTERED'] = '1'
    window_shape = (int(16/9 * 600), 720)

    pygame.init()
    clock = pygame.time.Clock()

    # Create window
    screen = pygame.display.set_mode(window_shape)
    pygame.display.set_caption(env.name)

    # Create menu
    menus, id_to_action = make_menus(env.world, window_shape)

    # Create inventory widget
    inv_widget = InventoryWidget(
        env.player.inventory,
        env.world.resources_path,
        env.world.font_path,
        position=(int(0.15 * window_shape[0]), int(0.15 * window_shape[0])),
        window_shape=window_shape
    )

    # Create zone widget
    zone_widget = ZoneWidget(
        env.world.zones,
        env.world.zone_properties,
        env.world.resources_path,
        env.world.font_path,
        position=(int(0.52 * window_shape[0]), int(0.02 * window_shape[0])),
        window_shape=window_shape
    )

    score_widget = ScoreWidget(
        env.world.font_path,
        position=(int(0.17 * window_shape[0]), int(0.01 * window_shape[0])),
        font_size=int(0.06 * window_shape[0]),
    )

    step_widget = StepLeftWidget(
        env.world.font_path,
        position=(int(0.17 * window_shape[0]), int(0.06 * window_shape[0])),
        font_size=int(0.04 * window_shape[0]),
    )

    return {
        'clock': clock,
        'screen': screen,
        'menus': menus,
        'widgets': (score_widget, zone_widget, inv_widget, step_widget),
        'id_to_action': id_to_action
    }

def update_rendering(
        env: CraftingEnv,
        clock:Clock,
        screen:pygame.Surface,
        menus:List[pygame_menu.Menu],
        widgets:List[EnvWidget],
        id_to_action:Dict[str, Any],
        additional_events:List[Event]=None,
        fps:float=60
    ) -> Union[int, None]:
    """ Update the User Interface returning action if one was found.

    Args:
        env: The running Crafting environment.
        clock: The used pygame clock.
        screen: The pygame screen.
        menus: List of menus.
        widgets: List of widgets.
        id_to_action: Mapping of buttons ids to actions.
        additional_events (Optional): Additional pygame events to simulate.
        fps: frames_per_seconds

    Returns:
        Action found while updating the UI. (can be None)

    """
    # Tick
    clock.tick(fps)

    # Paint background
    screen.fill((198, 198, 198))

    # Execute main from principal menu if is enabled
    events = pygame.event.get()
    if additional_events is not None:
        events += additional_events
    for event in events:
        if event.type == pygame.QUIT:
            exit()

    for widget in widgets:
        widget.update(env)
        widget.draw(screen)

    action = None
    action_is_legal = env.get_action_is_legal()

    for menu in menus:
        buttons = [
            widget for widget in menu.get_widgets()
            if isinstance(widget, pygame_menu.widgets.Button)
        ]
        for button in buttons:
            action_id = env.action(*id_to_action[button.get_id()])
            show_button = action_is_legal[action_id]
            if show_button:
                button.show()
            else:
                button.hide()

        menu.update(events)
        menu.draw(screen)

        selected_widget = menu.get_selected_widget()
        if selected_widget is not None and selected_widget.update(events):
            action = selected_widget.apply()

    # Update surface
    pygame.display.update()
    return action

def surface_to_rgb_array(surface: pygame.Surface) -> np.ndarray:
    """ Transforms a pygame surface to a conventional rgb array.
    
    Args:
        surface: pygame surface.
    
    Returns:
        A rgb_array representing the given surface.
    
    """
    return pygame.surfarray.array3d(surface).swapaxes(0, 1)

def make_menus(world: World, window_shape: tuple):
    """ Build menus for user interface.

    Args:
        world: The current world.
        window_shape: Shape of the window containing menus.

    """

    def add_button(menu: Menu, id_to_action:Dict[str, Any], image_path:str,
            scaling:float, text_width:int, action_type, identificator, padding):
        image = pygame_menu.baseimage.BaseImage(image_path).scale(scaling, scaling)

        button = menu.add.button(' '*text_width, lambda *args: args, action_type,
            identificator, padding=padding)

        decorator = button.get_decorator()
        decorator.add_baseimage(0, 0, image, centered=True)
        id_to_action[button.get_id()] = (action_type, identificator) 

    resources_path = world.resources_path
    id_to_action = {}

    # Item Menu
    items_menu_height = int(0.75 * window_shape[1])
    items_menu_width = int(0.15 * window_shape[0])

    items_menu = pygame_menu.Menu(
        title='Search',
        height=items_menu_height,
        width=items_menu_width,
        keyboard_enabled=False,
        joystick_enabled=False,
        position=(0, 0),
        overflow=(True, False),
        theme=pygame_menu.themes.THEME_BLUE,
    )

    items_images_path = os.path.join(resources_path, 'items')
    for item in world.searchable_items:
        image_path = os.path.join(items_images_path, f"{item.item_id}.png")
        add_button(items_menu, id_to_action, image_path, scaling=0.5, text_width=8,
            action_type='get', identificator=item.item_id, padding=(12, 0, 12, 0))

    # Recipes Menu
    recipes_menu_height = window_shape[1] - items_menu_height
    recipes_menu_width = window_shape[0]

    recipes_menu = pygame_menu.Menu(
        title='Craft',
        height=recipes_menu_height,
        width=recipes_menu_width,
        keyboard_enabled=False,
        joystick_enabled=False,
        rows=1,
        columns=world.n_recipes,
        position=(0, 100),
        overflow=(False, True),
        column_max_width=int(0.08 * window_shape[0]),
        theme=pygame_menu.themes.THEME_ORANGE
    )

    recipes_images_path = os.path.join(resources_path, 'items')
    for recipe in world.recipes:
        image_path = os.path.join(recipes_images_path, f"{recipe.recipe_id}.png")
        add_button(recipes_menu, id_to_action, image_path, scaling=0.5, text_width=8,
            action_type='craft', identificator=recipe.recipe_id, padding=(16, 0, 16, 0))

    # Zones Menu
    zones_menu_height = items_menu_height
    zones_menu_width = int(0.20 * window_shape[0])

    zones_menu = pygame_menu.Menu(
        title='Move',
        height=zones_menu_height,
        width=zones_menu_width,
        keyboard_enabled=False,
        joystick_enabled=False,
        position=(100, 0),
        overflow=(True, False),
        theme=pygame_menu.themes.THEME_GREEN,
    )

    zones_images_path = os.path.join(resources_path, 'zones')
    for zone in world.zones:
        image_path = os.path.join(zones_images_path, f"{zone.zone_id}.png")
        add_button(zones_menu, id_to_action, image_path, scaling=0.2, text_width=19,
            action_type='move', identificator=zone.zone_id, padding=(26, 0, 26, 0))

    return (items_menu, recipes_menu, zones_menu), id_to_action


if __name__ == '__main__':
    from crafting.examples.minecraft.items import ENCHANTING_TABLE
    from crafting.examples import MineCraftingEnv

    env = MineCraftingEnv(verbose=1, max_step=100,
        tasks=['obtain_enchanting_table'], tasks_can_end=[True]
    )

    draw_requirements_graph = False
    if draw_requirements_graph:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        env.world.draw_requirements_graph(ax)
        plt.show()

    ALL_GET_OPTIONS = env.world.get_all_options()

    enchant_table_option = ALL_GET_OPTIONS[f"Get {ENCHANTING_TABLE}"]
    # print(enchant_table_option)

    for _ in range(2):
        observation = env.reset()
        done = False
        total_reward = 0
        while not done:
            rgb_array = env.render(mode='rgb_array')

            enchant_action_id, _ = enchant_table_option(observation)
            print(f'For Enchanting Table: {env.action_from_id(enchant_action_id)}')

            action = get_human_action(env, **env.render_variables)
            action_id = env.action(*action)
            print(f'Human did: {env.action_from_id(action_id)}')

            observation, reward, done, infos = env(action_id)
            total_reward += reward

        print("SCORE: ", total_reward)