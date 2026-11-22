"""Headless smoke test: drives every scene with fake key presses.

Usage:  python tools/smoke_test.py [screenshot_dir]
"""
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import tempfile  # noqa: E402
_tmp = tempfile.mkdtemp()
os.environ["JRPG_SAVE_DB"] = os.path.join(_tmp, "smoke.db")   # never touch real saves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from engine.game_engine import GameEngine  # noqa: E402
from scenes.battle_scene import BattleScene  # noqa: E402
from scenes.title_scene import TitleScene  # noqa: E402

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
assert eng.scenes.top.menu.items[1][1] is False   # 이어하기 disabled with no saves
tap(pygame.K_z, 40)
assert top() == "WorldScene", top()
w = eng.scenes.top
st = eng.state
assert (st.map, w.player.gx, w.player.gy) == ("village", 4, 6)
# talk to the chief at (5,7): step right, then face down (blocked by the NPC)
tap(pygame.K_RIGHT); tap(pygame.K_DOWN)
assert (w.player.gx, w.player.gy) == (5, 6), (w.player.gx, w.player.gy)
tap(pygame.K_z, 120); shot("2_dialogue")
assert w.dialogue is not None
for _ in range(4):
    if w.dialogue is None:
        break
    tap(pygame.K_z, 60)
assert w.dialogue is None
# tree collision on the west edge
hold(pygame.K_LEFT, 120)
assert w.player.gx == 1, w.player.gx
shot("3_field")
# chest at (20,3)
w.player.place(19, 3, "right")
potions = st.inventory.get("potion", 0)
tap(pygame.K_z, 90); shot("3b_chest")
tap(pygame.K_z, 30)
assert st.inventory["potion"] == potions + 2 and "chest:village:village_chest_1" in st.flags
tap(pygame.K_z, 90)                      # empty now
assert st.inventory["potion"] == potions + 2
tap(pygame.K_z, 30)
# menu overlay -> item screen: drink a potion
tap(pygame.K_c); shot("4_menu")
assert top() == "MenuScene" and len(eng.scenes.stack) == 2
st.leader.hp = 10
tap(pygame.K_z, 30)
assert top() == "ItemScene", top()
eng.scenes.top.menu.index = eng.scenes.top.ids.index("potion")
tap(pygame.K_z, 60); shot("4b_items")
assert st.leader.hp == 30 and st.inventory["potion"] == potions + 1, (st.leader.hp, st.inventory)
tap(pygame.K_z, 30); tap(pygame.K_x)
assert top() == "MenuScene", top()
# equipment: swap wood sword -> iron sword
st.add_item("iron_sword")
atk = st.leader.stat("atk")
eng.scenes.top.menu.index = 1
tap(pygame.K_z, 30)
assert top() == "EquipScene", top()
tap(pygame.K_z)                          # weapon slot
shot("4c_equip")
tap(pygame.K_z)                          # first candidate = iron_sword
assert st.leader.weapon == "iron_sword" and st.leader.stat("atk") == atk + 4
assert "iron_sword" not in st.inventory and st.inventory["wood_sword"] == 1
tap(pygame.K_x)
eng.scenes.top.menu.index = 2
tap(pygame.K_z, 30)
assert top() == "StatusScene", top()
shot("4d_status")
tap(pygame.K_x); tap(pygame.K_x)
assert top() == "WorldScene"
# warp south to the meadow
w.player.place(7, 12, "down")
tap(pygame.K_DOWN, 60)
assert top() == "WorldScene" and eng.scenes.top is not w, "warp did not happen"
w = eng.scenes.top
assert (st.map, w.player.gx, w.player.gy) == ("meadow", 7, 1), (st.map, w.player.gx, w.player.gy)
shot("4e_meadow")
# walk in tall grass until an encounter
w.player.place(4, 3, "down")
w.steps_to_encounter = 1
st.encounter_groups = lambda: [["slime", "bat"]]   # deterministic group
hold(pygame.K_DOWN, 60)
frames(40)
assert top() == "BattleScene", top()
b = eng.scenes.top
assert [e.id for e in b.bs.enemies] == ["slime", "bat"]
tap(pygame.K_z, 60)          # dismiss "appeared"
assert b.mode == "cmd", b.mode
shot("5_battle")
# skill menu -> 강타 -> pick 2nd enemy
mp = eng.state.leader.mp
tap(pygame.K_DOWN); tap(pygame.K_DOWN); tap(pygame.K_z)
assert b.mode == "skill", b.mode
shot("5b_skill")
tap(pygame.K_z)
assert b.mode == "target", b.mode
tap(pygame.K_RIGHT); shot("5c_target")
tap(pygame.K_z, 30)
assert b.mode == "msg" and eng.state.leader.mp == mp - 3, (b.mode, eng.state.leader.mp)
for _ in range(80):
    if top() != "BattleScene":
        break
    tap(pygame.K_z, 40)       # attack first alive enemy / advance messages
del st.encounter_groups
frames(60)
assert top() == "WorldScene", top()
assert len(eng.scenes.stack) == 1
st = eng.state
assert st.leader.exp > 0 or st.leader.level > 1, "battle rewards not applied"
assert st.gold > 50, st.gold
# save to slot 2 via menu
tap(pygame.K_c)
eng.scenes.top.menu.index = 3
tap(pygame.K_z, 30)
assert top() == "SaveSlotScene", top()
eng.scenes.top.menu.index = 1
tap(pygame.K_z, 120); shot("6_saved")
tap(pygame.K_z, 30)
assert top() == "MenuScene", top()
saved = (st.x, st.y, st.facing, st.gold, st.leader.level, st.leader.exp, st.leader.hp, dict(st.inventory))
# back to title via menu
eng.scenes.top.menu.index = 4
tap(pygame.K_z, 60)
assert top() == "TitleScene", top()
assert eng.state is None
title = eng.scenes.top
assert title.menu.items[1][1] is True    # 이어하기 enabled now
title.menu.index = 1
tap(pygame.K_z, 30)
assert top() == "SaveSlotScene", top()
slot_scene = eng.scenes.top
assert not slot_scene.menu.items[0][1] and slot_scene.menu.items[1][1]   # only slot 2 loadable
shot("7_load")
slot_scene.menu.index = 1
tap(pygame.K_z, 60)
assert top() == "WorldScene" and len(eng.scenes.stack) == 1, top()
st2, w2 = eng.state, eng.scenes.top
loaded = (st2.x, st2.y, st2.facing, st2.gold, st2.leader.level, st2.leader.exp, st2.leader.hp, dict(st2.inventory))
assert loaded == saved, (loaded, saved)
assert (w2.player.gx, w2.player.gy) == (st2.x, st2.y)
assert st2.slot == 2
# party wipe -> game over -> title
st2.leader.hp = 1
eng.scenes.push(BattleScene(eng, ["goblin", "goblin", "goblin"]), fade=False)
tap(pygame.K_z, 60)
tap(pygame.K_DOWN); tap(pygame.K_z, 30)      # 방어
for _ in range(30):
    if top() != "BattleScene":
        break
    tap(pygame.K_z, 40)
frames(60); shot("8_game_over")
assert top() == "GameOverScene", top()
assert eng.state is None
frames(70); tap(pygame.K_z, 60)
assert top() == "TitleScene", top()
eng.saves.close()
pygame.quit()
print("SMOKE TEST OK")
