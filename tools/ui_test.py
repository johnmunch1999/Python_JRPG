"""UI-level tests: list scrolling, map validation errors, level-up jingle timing.

Usage:  python tools/ui_test.py
"""
import os
import random
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["JRPG_SAVE_DB"] = os.path.join(tempfile.mkdtemp(), "ui.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from engine.game_engine import GameEngine  # noqa: E402
from engine.state_manager import GameState  # noqa: E402
from entities.character import exp_to_next  # noqa: E402
from gui.menu_list import MenuList  # noqa: E402
from systems import data_loader, field_map  # noqa: E402

eng = GameEngine()


class FakeInput:
    def __init__(self, *pressed):
        self.pressed = set(pressed)

    def was_pressed(self, action):
        return action in self.pressed


def test_menu_scrolls_with_cursor():
    m = MenuList(eng.resources, [f"item {i}" for i in range(12)], (0, 0, 100, 6 + 16 * 4))
    assert m.rows == 4 and list(m.visible()) == [0, 1, 2, 3]
    for _ in range(5):
        m.update(FakeInput("down"), 0.016)
    assert m.index == 5 and list(m.visible()) == [2, 3, 4, 5]
    for _ in range(6):
        m.update(FakeInput("up"), 0.016)          # 5 -> 0 -> wraps to 11
    assert m.index == 11 and list(m.visible()) == [8, 9, 10, 11]
    m.index = 0                                   # set directly, as scenes do
    m.draw(eng.screen)
    assert list(m.visible()) == [0, 1, 2, 3]
    assert m.row_y(2) == 6 + 32


def test_short_menu_does_not_scroll():
    m = MenuList(eng.resources, ["a", "b"], (0, 0, 100, 100))
    m.update(FakeInput("down"), 0.016)
    assert m.top == 0 and list(m.visible()) == [0, 1]


def test_item_screen_scrolls_with_many_items():
    from scenes.field_menus import ItemScene
    from scenes.world_scene import WorldScene
    eng.state = GameState.new_game()
    for iid in data_loader.items():
        eng.state.add_item(iid)
    for k in range(6):                       # fake extra entries to overflow the list
        data_loader.items()[f"test_{k}"] = {"name": f"테스트{k}", "type": "consumable",
                                             "effect": {"hp": 1}, "description": ""}
        eng.state.add_item(f"test_{k}")
    try:
        eng.scenes.change(WorldScene(eng), fade=False)
        eng.scenes.push(ItemScene(eng), fade=False)
        scene = eng.scenes.top
        assert len(scene.ids) > scene.menu.rows
        scene.menu.index = len(scene.ids) - 1
        eng.step(1 / 60)                      # draws without overflowing / crashing
        assert scene.menu.index in scene.menu.visible()
    finally:
        for k in range(6):
            data_loader.items().pop(f"test_{k}", None)
        eng.state = None


def test_validation_catches_bad_npc():
    village = field_map.meta("village")
    npc = next(o for o in village.objects if o.type == "npc")
    saved = dict(npc.props)
    try:
        npc.props.update(sprite=9, facing="sideways", wander=-1)
        errs = field_map.validate(data_loader.monsters(), data_loader.items())
        assert any("sprite 9" in e for e in errs), errs
        assert any("bad facing" in e for e in errs), errs
        assert any("bad wander" in e for e in errs), errs
    finally:
        npc.props.clear()
        npc.props.update(saved)
    assert field_map.validate(data_loader.monsters(), data_loader.items()) == []


def test_levelup_jingle_plays_with_its_page():
    from scenes.battle_scene import BattleScene
    from scenes.world_scene import WorldScene
    played = []
    res = eng.resources
    orig = res.jingle
    res.jingle = lambda name: (played.append(name), orig(name))
    try:
        eng.state = GameState.new_game()
        hero = eng.state.leader
        hero.exp = exp_to_next(1) - 1
        eng.scenes.change(WorldScene(eng), fade=False)
        eng.scenes.push(BattleScene(eng, ["slime"], random.Random(0)), fade=False)
        b = eng.scenes.top
        b.bs.enemies[0].hp = 1
        level_page_seen = False
        for _ in range(40):
            eng.step(1 / 60, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z)])
            eng.step(1 / 60, [pygame.event.Event(pygame.KEYUP, key=pygame.K_z)])
            for _ in range(20):
                eng.step(1 / 60)
            if b.box and any("레벨" in line for page in b.box.pages for line in page):
                level_page_seen = True
                assert played[-1] == "levelup", played
            if eng.scenes.top is not b:
                break
        assert hero.level == 2
        assert level_page_seen
        assert played == ["victory", "levelup"], played
    finally:
        res.jingle = orig
        eng.state = None


if __name__ == "__main__":
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_")]
    for name, fn in tests:
        fn()
        print("ok ", name)
    print(f"UI TESTS OK ({len(tests)})")
