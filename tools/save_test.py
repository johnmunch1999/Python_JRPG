"""Save system tests: round trip, flags, equipment and v1 -> v2 migration.

Usage:  python tools/save_test.py
"""
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.state_manager import GameState  # noqa: E402
from systems import data_loader  # noqa: E402
from systems.save_system import MIGRATIONS, SCHEMA_VERSION, SaveSystem  # noqa: E402

data_loader.load_all()


def test_round_trip_with_flags_and_equipment():
    s = SaveSystem(":memory:")
    g = GameState.new_game()
    g.flags = {"chest:meadow:meadow_chest_1", "talked:chief"}
    g.add_item("iron_sword")
    g.equip(g.leader, "weapon", "iron_sword")
    g.map, g.x, g.y = "meadow", 5, 5
    s.save(1, g)
    l = s.load(1)
    assert l.flags == g.flags
    assert l.leader.weapon == "iron_sword" and l.inventory.get("wood_sword") == 1
    assert (l.map, l.x, l.y) == ("meadow", 5, 5)
    # overwriting a slot replaces its flags instead of merging them
    l.flags = {"x"}
    s.save(1, l)
    assert s.load(1).flags == {"x"}


def test_migrates_v1_database():
    path = os.path.join(tempfile.mkdtemp(), "old.db")
    conn = sqlite3.connect(path)
    conn.executescript(MIGRATIONS[0] + "PRAGMA user_version = 1;")
    conn.execute("INSERT INTO save_slots VALUES (1, 1, '2026-01-01T00:00:00', 12, 'village', 4, 6, 'down', 99)")
    conn.execute("INSERT INTO party_members VALUES (1, 0, 'hero', 3, 5, 20, 8, 'wood_sword', NULL)")
    conn.execute("INSERT INTO inventory VALUES (1, 'potion', 2)")
    conn.commit()
    conn.close()

    s = SaveSystem(path)
    assert s.conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    g = s.load(1)
    assert g.gold == 99 and g.leader.level == 3 and g.inventory == {"potion": 2}
    assert g.flags == set()
    s.close()


def test_refuses_newer_schema():
    path = os.path.join(tempfile.mkdtemp(), "future.db")
    conn = sqlite3.connect(path)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
    conn.close()
    try:
        SaveSystem(path)
    except RuntimeError:
        return
    raise AssertionError("newer schema was accepted")


def test_equip_and_unequip():
    g = GameState.new_game()
    hero = g.leader
    g.equip(hero, "armor", None)
    assert hero.armor is None and g.inventory["cloth_armor"] == 1
    assert not g.equip(hero, "weapon", "iron_sword")      # not owned
    assert hero.weapon == "wood_sword"


def _engine_with_db(path):
    os.environ["SDL_VIDEODRIVER"] = os.environ["SDL_AUDIODRIVER"] = "dummy"
    import config
    config.SAVE_DB = path
    from engine.game_engine import GameEngine
    return GameEngine()


def test_corrupt_file_is_backed_up_not_fatal():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "game.db")
    with open(path, "w") as f:
        f.write("this is not a database")
    eng = _engine_with_db(path)
    assert eng.saves.has_any() is False
    assert eng.save_warning and "손상" in eng.save_warning[0]
    backups = [n for n in os.listdir(d) if n.startswith("game.db.broken-")]
    assert len(backups) == 1
    with open(os.path.join(d, backups[0])) as f:
        assert f.read() == "this is not a database"      # original kept
    eng.saves.save(1, GameState.new_game())                # fresh DB works
    eng.saves.close()


def test_newer_file_is_left_untouched():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "game.db")
    conn = sqlite3.connect(path)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 5}")
    conn.close()
    eng = _engine_with_db(path)
    eng.saves.save(1, GameState.new_game())                # goes to memory only
    assert sqlite3.connect(path).execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION + 5
    assert os.listdir(d) == ["game.db"]


def test_slot_with_unknown_character_fails_cleanly():
    s = SaveSystem(":memory:")
    s.save(1, GameState.new_game())
    s.conn.execute("UPDATE party_members SET char_id = 'removed_hero'")
    try:
        s.load(1)
    except KeyError:
        return   # SaveSlotScene turns this into a message instead of crashing
    raise AssertionError("expected KeyError")


if __name__ == "__main__":
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_")]
    for name, fn in tests:
        fn()
        print("ok ", name)
    print(f"SAVE TESTS OK ({len(tests)})")
