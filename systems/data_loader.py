"""Read-only game definitions loaded from data/*.json (cached, validated)."""
import json
import os

import config

_FILES = ("characters", "monsters", "skills", "items", "new_game")
_cache = {}


def _load(name):
    if name not in _cache:
        with open(os.path.join(config.DATA_DIR, name + ".json"), encoding="utf-8") as f:
            _cache[name] = json.load(f)
    return _cache[name]


def characters(): return _load("characters")
def monsters(): return _load("monsters")
def skills(): return _load("skills")
def items(): return _load("items")
def new_game(): return _load("new_game")


def reload():
    _cache.clear()


def validate():
    """Check cross-references between files. Returns a list of problems (empty = OK)."""
    errs = []
    sk, it, ch, mo, ng = skills(), items(), characters(), monsters(), new_game()
    for cid, c in ch.items():
        errs += [f"character {cid}: unknown skill {s}" for s in c.get("skills", []) if s not in sk]
        for key in ("hp", "mp", "atk", "def", "agi"):
            if key not in c["base"]:
                errs.append(f"character {cid}: base.{key} missing")
    for mid, m in mo.items():
        errs += [f"monster {mid}: unknown drop {d['item']}" for d in m.get("drops", []) if d["item"] not in it]
    errs += [f"new_game: unknown character {c}" for c in ng["party"] if c not in ch]
    errs += [f"new_game: unknown item {i}" for i in ng["inventory"] if i not in it]
    for cid, eq in ng.get("equipment", {}).items():
        errs += [f"new_game: {cid} equips unknown {i}" for i in eq.values() if i and i not in it]
    for mid, m in mo.items():
        errs += [f"monster {mid}: unknown ai skill {a['skill']}" for a in m.get("ai", []) if a["skill"] not in sk]
    from systems import field_map   # maps reference monsters/items, so check them here too
    errs += field_map.validate(mo, it)
    loc = ng["location"]
    if loc["map"] not in field_map.all_map_ids():
        errs.append(f"new_game: unknown map {loc['map']}")
    elif field_map.meta(loc["map"]).solid(loc["x"], loc["y"]):
        errs.append("new_game: start position is blocked")
    for mid, m in mo.items():
        errs += [f"monster {mid}: unknown drop {d['item']}" for d in m.get("drops", []) if d["item"] not in it]
    for sid, s in sk.items():
        if s.get("kind") not in ("damage", "heal"):
            errs.append(f"skill {sid}: bad kind {s.get('kind')}")
        if s.get("target") not in ("enemy", "all_enemies", "ally", "all_allies", "self"):
            errs.append(f"skill {sid}: bad target {s.get('target')}")
    return errs


def load_all():
    for name in _FILES:
        _load(name)
    errs = validate()
    if errs:
        raise ValueError("Invalid game data:\n  " + "\n  ".join(errs))
