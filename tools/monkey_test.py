"""Random-input soak test: mashes keys across every scene and checks invariants.

Usage:  python tools/monkey_test.py [seeds=20] [frames=6000]
"""
import os
import random
import sys
import tempfile
import traceback

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["JRPG_SAVE_DB"] = os.path.join(tempfile.mkdtemp(), "monkey.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from engine.game_engine import GameEngine  # noqa: E402
from scenes.title_scene import TitleScene  # noqa: E402

KEYS = [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_z, pygame.K_x, pygame.K_c]
WEIGHTS = [5, 5, 5, 5, 8, 2, 1]


def check(eng):
    stack = eng.scenes.stack
    assert stack, "scene stack is empty"
    st = eng.state
    names = [type(s).__name__ for s in stack]
    if any(n in ("WorldScene", "BattleScene", "MenuScene") for n in names):
        assert st is not None, f"no game state in {names}"
    if st is None:
        return
    for c in st.party:
        assert 0 <= c.hp <= c.max_hp, (c.name, c.hp, c.max_hp)
        assert 0 <= c.mp <= c.max_mp, (c.name, c.mp, c.max_mp)
        assert c.exp >= 0 and c.level >= 1
    assert st.gold >= 0
    assert all(q > 0 for q in st.inventory.values()), st.inventory
    world = next((s for s in stack if type(s).__name__ == "WorldScene"), None)
    if world and getattr(world, "map", None) and world.map.id == st.map:
        p = world.player
        assert not world.map.solid(p.gx, p.gy), ("player in wall", st.map, p.gx, p.gy)
        for n in world.npcs:
            assert (n.gx, n.gy) != (p.gx, p.gy), ("player overlaps npc", n.obj.name)
            assert not world.map.solid(n.gx, n.gy), ("npc in wall", n.obj.name)


def run(seed, frames):
    rnd = random.Random(seed)
    random.seed(seed)
    eng = GameEngine()
    if seed % 2:   # odd seeds start in the meadow's tall grass so battles happen
        from engine.state_manager import GameState
        from scenes.world_scene import WorldScene
        eng.state = GameState.new_game()
        eng.state.map, eng.state.x, eng.state.y = "meadow", 4, 4
        eng.scenes.change(WorldScene(eng), fade=False)
    else:
        eng.scenes.change(TitleScene(eng), fade=False)
    held, hold_left = None, 0
    seen = set()
    for f in range(frames):
        events = []
        if hold_left <= 0:
            if held is not None:
                events.append(pygame.event.Event(pygame.KEYUP, key=held))
                held = None
            if rnd.random() < 0.5:
                held = rnd.choices(KEYS, WEIGHTS)[0]
                hold_left = rnd.choice((1, 2, 6, 20, 40))
                events.append(pygame.event.Event(pygame.KEYDOWN, key=held))
            else:
                hold_left = rnd.randint(1, 15)
        hold_left -= 1
        eng.step(1 / 60, events)
        # keep the run inside the game: restart from the title if "종료" was chosen
        eng.running = True
        seen.update(type(s).__name__ for s in eng.scenes.stack)
        if seed % 4 == 1 and eng.state and f % 900 == 0 and eng.state.leader.hp < 8:
            eng.state.leader.hp = eng.state.leader.max_hp   # avoid ending every run in game over
        check(eng)
    return seen


if __name__ == "__main__":
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    frames = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
    all_seen, failures = set(), 0
    for seed in range(seeds):
        try:
            all_seen |= run(seed, frames)
        except Exception:
            failures += 1
            print(f"--- seed {seed} FAILED ---")
            traceback.print_exc()
    print("scenes visited:", ", ".join(sorted(all_seen)))
    if failures:
        print(f"MONKEY TEST FAILED ({failures}/{seeds})")
        sys.exit(1)
    print(f"MONKEY TEST OK ({seeds} seeds x {frames} frames)")
