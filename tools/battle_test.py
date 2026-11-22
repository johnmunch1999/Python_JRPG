"""Unit tests for systems/battle_system.py (no pygame needed).

Usage:  python tools/battle_test.py
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.state_manager import GameState  # noqa: E402
from systems import data_loader  # noqa: E402
from systems.battle_system import ENEMY, PARTY, Action, BattleSystem  # noqa: E402

data_loader.load_all()


def fresh(group, seed=0):
    st = GameState.new_game()
    return st, BattleSystem(st, group, random.Random(seed))


def test_names_get_suffix_for_duplicates():
    _, b = fresh(["slime", "slime", "bat"])
    assert [e.name for e in b.enemies] == ["슬라임 A", "슬라임 B", "박쥐"]


def test_attack_until_victory_and_rewards():
    st, b = fresh(["slime"])
    for _ in range(10):
        b.run_round({0: Action("attack", 0)})
        if b.result:
            break
    assert b.result == "victory"
    gold = st.gold
    lines = b.apply_rewards()
    assert st.gold == gold + 3 and st.leader.exp == 4, (st.gold, st.leader.exp)
    assert "경험치 4" in lines[0]


def test_dead_target_retargets():
    _, b = fresh(["slime", "slime"])
    b.enemies[0].hp = 0
    b.run_round({0: Action("attack", 0)})
    assert b.enemies[1].hp < b.enemies[1].max_hp


def test_skill_costs_mp_and_all_enemies_hits_everyone():
    st, b = fresh(["slime", "bat"])
    mp = st.leader.mp
    b.run_round({0: Action("skill", None, "whirl")})
    assert st.leader.mp == mp - 5
    assert all(e.hp < e.max_hp for e in b.enemies)


def test_not_enough_mp():
    st, b = fresh(["slime"])
    st.leader.mp = 1
    events = b.run_round({0: Action("skill", 0, "slash")})
    assert any("MP가 부족" in l for e in events for l in e.lines)
    assert st.leader.mp == 1


def test_heal_skill_and_item():
    st, b = fresh(["slime"])
    hero = st.leader
    hero.hp = 5
    b.run_round({0: Action("skill", 0, "heal")})
    assert hero.hp > 5
    hero.hp = 5
    potions = st.inventory["potion"]
    b.run_round({0: Action("item", 0, "potion")})
    assert st.inventory.get("potion", 0) == potions - 1
    assert hero.hp > 5


def test_last_item_removed_from_bag():
    st, b = fresh(["slime"])
    st.inventory = {"ether": 1}
    st.leader.mp = 0
    b.run_round({0: Action("item", 0, "ether")})
    assert "ether" not in st.inventory and st.leader.mp > 0
    assert b.usable_items() == []


def test_defend_halves_damage():
    totals = []
    for defend in (False, True):
        dmg = 0
        for seed in range(40):
            st, b = fresh(["goblin"], seed)
            b.enemies[0].data = dict(b.enemies[0].data, ai=[{"skill": "attack", "weight": 1}])
            b.run_round({0: Action("defend")} if defend else {0: Action("attack", 0)})
            dmg += st.leader.max_hp - st.leader.hp
        totals.append(dmg)
    assert totals[1] < totals[0] * 0.7, totals


def test_defeat():
    st, b = fresh(["goblin", "goblin", "goblin"])
    st.leader.hp = 1
    b.run_round({0: Action("defend")})
    assert b.result == "defeat" and st.leader.hp == 0


def test_flee_eventually_works_and_failure_costs_turn():
    outcomes = set()
    for seed in range(30):
        st, b = fresh(["goblin"], seed)
        events = b.run_round({0: Action("flee")})
        outcomes.add(b.result)
        if b.result is None:
            assert "도망칠 수 없었다" in events[0].lines[0]
            assert b.enemies[0].hp == b.enemies[0].max_hp  # party did nothing
    assert outcomes == {"fled", None}, outcomes


def test_ai_conditions():
    _, b = fresh(["slime"])
    picks = {b._enemy_ai(0).id for _ in range(50)}
    assert picks == {"attack"}, picks           # regen only below 50% HP
    b.enemies[0].hp = 2
    picks = {b._enemy_ai(0).id for _ in range(100)}
    assert "regen" in picks, picks


def test_events_carry_snapshots():
    _, b = fresh(["slime"])
    events = b.run_round({0: Action("attack", 0)})
    hits = [e for e in events if e.hit == (ENEMY, 0)]
    assert hits and hits[0].snap[ENEMY][0] < b.enemies[0].max_hp
    assert PARTY in hits[0].snap


def test_same_seed_same_result():
    runs = []
    for _ in range(2):
        _, b = fresh(["slime", "bat"], seed=7)
        lines = []
        while not b.result:
            lines += [l for e in b.run_round({0: Action("attack", 0)}) for l in e.lines]
        runs.append(lines)
    assert runs[0] == runs[1]


if __name__ == "__main__":
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_")]
    for name, fn in tests:
        fn()
        print("ok ", name)
    print(f"BATTLE TESTS OK ({len(tests)})")
