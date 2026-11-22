"""Turn-based battle rules. Pure logic (no pygame) so it can be unit-tested.

Round flow: the player picks one action per living party member, then
run_round() sorts everyone by agility and resolves actions in order.
Each resolved action produces an Event that the scene shows one page at a time;
the event carries an HP/MP snapshot so the bars change in sync with the text.
"""
import random
from dataclasses import dataclass, field

from entities.enemy import Enemy
from systems import data_loader

PARTY, ENEMY = "party", "enemy"
CRIT_CHANCE = 1 / 16


@dataclass
class Action:
    kind: str                  # attack | defend | skill | item | flee
    target: int | None = None  # index into the target side (single-target only)
    id: str | None = None      # skill_id / item_id


@dataclass
class Event:
    lines: list
    hit: tuple | None = None   # (side, index) that took damage -> shake/flash
    sound: str | None = None   # "hit" | "heal" | "miss" | None
    snap: dict = field(default_factory=dict)
    target: tuple | None = None  # (side, index) the number/effect is drawn on
    amount: int | None = None    # damage or healing shown as a popup number
    fx: str | None = None        # visual effect name from skills.json ("slash", "heal", "wave", ...)
    crit: bool = False


class BattleSystem:
    def __init__(self, state, monster_ids, rng=None):
        self.state = state
        self.rng = rng or random.Random()
        self.party = state.party
        counts = {m: monster_ids.count(m) for m in monster_ids}
        seen = {}
        self.enemies = []
        for m in monster_ids:
            seen[m] = seen.get(m, 0) + 1
            suffix = " " + "ABCDEFG"[seen[m] - 1] if counts[m] > 1 else ""
            self.enemies.append(Enemy(m, suffix))
        self.result = None   # None | victory | defeat | fled
        self.defending = set()
        self.turn = 0

    # --- helpers ----------------------------------------------------
    def side(self, name):
        return self.party if name == PARTY else self.enemies

    def alive(self, name):
        return [i for i, b in enumerate(self.side(name)) if b.alive]

    def snapshot(self):
        return {PARTY: [(c.hp, c.mp) for c in self.party],
                ENEMY: [e.hp for e in self.enemies]}

    def _event(self, lines, hit=None, sound=None, **extra):
        return Event(lines if isinstance(lines, list) else [lines], hit, sound, self.snapshot(), **extra)

    def usable_skills(self, char):
        """[(skill_id, enough_mp)] for the skill submenu."""
        sk = data_loader.skills()
        return [(sid, char.mp >= sk[sid]["mp"]) for sid in char.skills]

    def usable_items(self):
        """[(item_id, qty)] consumables in the bag."""
        it = data_loader.items()
        return [(iid, q) for iid, q in self.state.inventory.items()
                if it[iid]["type"] == "consumable" and q > 0]

    def damage(self, atk, df, power=1.0, crit=False):
        base = atk * power * 1.5 if crit else atk * power - df / 2
        return max(1, round(base * self.rng.uniform(0.9, 1.1)))

    # --- round ------------------------------------------------------
    def run_round(self, commands):
        """commands: {party_index: Action}. Returns list[Event]."""
        self.turn += 1
        self.defending = {(PARTY, i) for i, a in commands.items() if a.kind == "defend"}
        events = []

        if any(a.kind == "flee" for a in commands.values()):
            if self._try_flee():
                self.result = "fled"
                return [self._event("무사히 도망쳤다!")]
            events.append(self._event("도망칠 수 없었다!", sound="miss"))
            commands = {}   # the whole party loses the turn

        actors = [(PARTY, i) for i in commands] + [(ENEMY, i) for i in self.alive(ENEMY)]
        actors.sort(key=lambda a: self.side(a[0])[a[1]].stat("agi") + self.rng.randint(0, 3),
                    reverse=True)
        for side, i in actors:
            if not self.side(side)[i].alive:
                continue
            action = commands[i] if side == PARTY else self._enemy_ai(i)
            events += self._execute(side, i, action)
            if self._check_end():
                break
        self._check_end()
        return events

    def _try_flee(self):
        p = [self.party[i].stat("agi") for i in self.alive(PARTY)]
        e = [self.enemies[i].stat("agi") for i in self.alive(ENEMY)]
        chance = 0.5 + (sum(p) / len(p) - sum(e) / len(e)) * 0.05
        return self.rng.random() < min(0.95, max(0.2, chance))

    def _check_end(self):
        if self.result:
            return True
        if not self.alive(ENEMY):
            self.result = "victory"
        elif not self.alive(PARTY):
            self.result = "defeat"
        return self.result is not None

    # --- monster AI -------------------------------------------------
    def _enemy_ai(self, i):
        """Weighted pick from monsters.json "ai"; entries may have "when": "hp_below:0.5"."""
        me = self.enemies[i]
        options = []
        for entry in me.data.get("ai", [{"skill": "attack", "weight": 1}]):
            cond = entry.get("when")
            if cond and cond.startswith("hp_below:") and me.hp / me.max_hp >= float(cond.split(":")[1]):
                continue
            options.append(entry)
        entry = self.rng.choices(options, weights=[o["weight"] for o in options])[0]
        sid = entry["skill"]
        kind = data_loader.skills()[sid]["target"]
        target = None
        if kind == "enemy":
            target = self.rng.choice(self.alive(PARTY))
        elif kind == "ally":   # heal the most hurt monster
            target = min(self.alive(ENEMY), key=lambda j: self.enemies[j].hp / self.enemies[j].max_hp)
        return Action("attack" if sid == "attack" else "skill", target, sid)

    # --- resolution -------------------------------------------------
    def _targets(self, side, i, kind, target):
        """Resolve a target spec into [(side, index)], retargeting if the pick has died."""
        foe = ENEMY if side == PARTY else PARTY
        if kind == "self":
            return [(side, i)]
        if kind in ("all_enemies", "all_allies"):
            s = foe if kind == "all_enemies" else side
            return [(s, j) for j in self.alive(s)]
        s = foe if kind == "enemy" else side
        alive = self.alive(s)
        if not alive:
            return []
        if target not in alive:
            if kind == "enemy":
                target = alive[0]
            else:
                target = min(alive, key=lambda j: self.side(s)[j].hp / self.side(s)[j].max_hp)
        return [(s, target)]

    def _execute(self, side, i, a):
        actor = self.side(side)[i]
        if a.kind == "defend":
            return [self._event(f"{actor.name}은(는) 방어 태세를 취했다.")]

        if a.kind == "item":
            item = data_loader.items()[a.id]
            if not self.state.remove_item(a.id):
                return [self._event(f"{item['name']}이(가) 더 이상 없다!", sound="miss")]
            events = [self._event(f"{actor.name}은(는) {item['name']}을(를) 사용했다.")]
            for s, j in self._targets(side, i, "ally", a.target):
                eff = item["effect"]
                events.append(self._restore(s, j, eff.get("hp", 0), eff.get("mp", 0)))
            return events

        sid = a.id or "attack"
        skill = data_loader.skills()[sid]
        if skill["mp"] > actor.mp:
            return [self._event(f"{actor.name}은(는) MP가 부족하다!", sound="miss")]
        actor.mp -= skill["mp"]
        targets = self._targets(side, i, skill["target"], a.target)
        head = f"{actor.name}의 공격!" if sid == "attack" else f"{actor.name}의 {skill['name']}!"
        events = []
        for s, j in targets:
            if skill["kind"] == "heal":
                ev = self._restore(s, j, skill.get("heal", 0), 0, skill.get("fx", "heal"))
            else:
                ev = self._hit(actor, s, j, skill.get("power", 1.0), crit_ok=sid == "attack",
                               fx=skill.get("fx", "slash"))
            events.append(ev)
        if events:
            events[0].lines.insert(0, head)
        return events

    def _hit(self, actor, s, j, power, crit_ok, fx="slash"):
        target = self.side(s)[j]
        crit = crit_ok and self.rng.random() < CRIT_CHANCE
        dmg = self.damage(actor.stat("atk"), target.stat("def"), power, crit)
        if (s, j) in self.defending:
            dmg = max(1, dmg // 2)
        target.hp = max(0, target.hp - dmg)
        lines = ["회심의 일격!"] if crit else []
        lines.append(f"{target.name}에게 {dmg}의 피해.")
        if not target.alive:
            lines.append(f"{target.name}을(를) 쓰러뜨렸다!" if s == ENEMY else f"{target.name}은(는) 쓰러졌다...")
        return self._event(lines, hit=(s, j), sound="crit" if crit else "hit",
                           target=(s, j), amount=dmg, fx=fx, crit=crit)

    def _restore(self, s, j, hp, mp, fx="heal"):
        t = self.side(s)[j]
        before_hp, before_mp = t.hp, t.mp
        t.hp = min(t.max_hp, t.hp + hp)
        t.mp = min(t.max_mp, t.mp + mp)
        parts = []
        if t.hp > before_hp:
            parts.append(f"HP {t.hp - before_hp}")
        if t.mp > before_mp:
            parts.append(f"MP {t.mp - before_mp}")
        text = f"{t.name}의 {', '.join(parts)} 회복." if parts else "하지만 효과가 없었다."
        gained = t.hp - before_hp or t.mp - before_mp or None
        return self._event(text, sound="heal", target=(s, j), amount=gained, fx=fx)

    # --- after battle -----------------------------------------------
    def apply_rewards(self):
        """Give exp/gold/drops to the state. Returns message lines."""
        exp = sum(e.data["exp"] for e in self.enemies)
        gold = sum(e.data["gold"] for e in self.enemies)
        self.state.gold += gold
        lines = [f"경험치 {exp}, {gold} G를 얻었다."]
        for i in self.alive(PARTY):
            c = self.party[i]
            if c.gain_exp(exp):
                lines.append(f"{c.name}은(는) 레벨 {c.level}이(가) 되었다!")
        for e in self.enemies:
            for drop in e.data.get("drops", []):
                if self.rng.random() < drop["chance"]:
                    self.state.add_item(drop["item"])
                    lines.append(f"{data_loader.items()[drop['item']]['name']}을(를) 손에 넣었다.")
        return lines
