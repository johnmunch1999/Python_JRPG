"""Headless smoke test: drives every scene with fake key presses.

Usage:  python tools/smoke_test.py [screenshot_dir]
"""
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from engine.game_engine import GameEngine  # noqa: E402
from scenes.battle_scene import BattleScene  # noqa: E402
from scenes.menu_scene import MenuScene  # noqa: E402
from scenes.title_scene import TitleScene  # noqa: E402
from scenes.world_scene import WorldScene  # noqa: E402

DT = 1 / 60
shots = sys.argv[1] if len(sys.argv) > 1 else None
random.seed(1)
eng = GameEngine()
eng.scenes.change(TitleScene(eng), fade=False)


def frames(n=1, events=()):
    for i in range(n):
        eng.step(DT, events if i == 0 else ())


def tap(key, wait=20):
    frames(1, [pygame.event.Event(pygame.KEYDOWN, key=key)])
    frames(1, [pygame.event.Event(pygame.KEYUP, key=key)])
    frames(wait)


def hold(key, n):
    frames(1, [pygame.event.Event(pygame.KEYDOWN, key=key)])
    frames(n)
    frames(1, [pygame.event.Event(pygame.KEYUP, key=key)])
    frames(20)


def shot(name):
    if shots:
        os.makedirs(shots, exist_ok=True)
        pygame.image.save(eng.screen, os.path.join(shots, name + ".png"))


def top():
    return type(eng.scenes.top).__name__


frames(30); shot("1_title")
tap(pygame.K_z, 40)
assert top() == "WorldScene", top()
w = eng.scenes.top
# talk to NPC: player at (3,2), NPC at (4,4). Move down 2, face right.
tap(pygame.K_DOWN); tap(pygame.K_DOWN); tap(pygame.K_RIGHT)
assert (w.player.gx, w.player.gy) == (3, 4), (w.player.gx, w.player.gy)  # blocked by NPC
tap(pygame.K_z, 120); shot("2_dialogue")
assert w.dialogue is not None
for _ in range(4):
    if w.dialogue is None:
        break
    tap(pygame.K_z, 60)
assert w.dialogue is None
# wall collision
hold(pygame.K_LEFT, 120)
assert w.player.gx == 1, w.player.gx
shot("3_field")
# menu overlay
tap(pygame.K_c); shot("4_menu")
assert top() == "MenuScene" and len(eng.scenes.stack) == 2
tap(pygame.K_x)
assert top() == "WorldScene"
# walk in tall grass until an encounter
tap(pygame.K_RIGHT); tap(pygame.K_RIGHT); tap(pygame.K_RIGHT)   # x=4, grass column
w.steps_to_encounter = 1
hold(pygame.K_DOWN, 60)
frames(40)
assert top() == "BattleScene", top()
b = eng.scenes.top
tap(pygame.K_z, 60)          # dismiss "appeared"
shot("5_battle")
for _ in range(12):
    if top() != "BattleScene":
        break
    tap(pygame.K_z, 60)       # attack / advance messages
frames(60)
assert top() == "WorldScene", top()
assert len(eng.scenes.stack) == 1
# back to title via menu
tap(pygame.K_c)
tap(pygame.K_DOWN); tap(pygame.K_DOWN)   # 아이템 -> wraps: index 4 is 타이틀로
m = eng.scenes.top
m.menu.index = 4
tap(pygame.K_z, 60)
assert top() == "TitleScene", top()
pygame.quit()
print("SMOKE TEST OK")
