"""Battle screen: command input, target selection and event playback.

All rules live in systems/battle_system.py; this scene only collects commands
and shows the resulting events one by one.
"""
import math
import random

import pygame

import config
from engine.scene import Scene
from gui import effects
from gui.dialogue_box import DialogueBox
from gui.menu_list import MenuList
from gui.window import draw_cursor, draw_text, draw_window
from systems import data_loader
from systems.battle_system import ENEMY, PARTY, Action, BattleSystem

BG = "backgrounds/nidhoggn_battlebacks/battleback{}.png"
MONSTER = "monsters/isaiah658_50_monsters/Monsters/Normal Colors/Monster #{} Front Normal Color Palette.png"
CMD_RECT = (4, 150, 80, 88)
INFO_RECT = (88, 150, 228, 88)
COLOR_LOW = (255, 112, 96)


class BattleScene(Scene):
    def __init__(self, engine, monster_ids=None, rng=None):
        super().__init__(engine)
        self.monster_ids = monster_ids
        self.rng = rng

    # --- setup ------------------------------------------------------
    def on_enter(self):
        st = self.engine.state
        ids = self.monster_ids or random.choice(st.encounter_groups() or [["slime"]])
        self.bs = BattleSystem(st, list(ids), self.rng)
        self.font = self.res.font(config.FONT_MAIN, config.FONT_SIZE)
        self.small = self.res.font(config.FONT_SMALL, config.FONT_SIZE_SMALL)
        bg = self.res.image(BG.format(random.randint(1, 10)))
        self.bg = pygame.transform.scale(bg, (config.VIRTUAL_W, 148))
        self._layout_enemies()

        self.disp = self.bs.snapshot()   # what the HP bars currently show
        self.shake = {}                  # (side, i) -> seconds left
        self.dying = {}                  # enemy index -> seconds into its death fade
        self.fx = []                     # active gui.effects
        self.intro = effects.BattleIntro()
        self.popup_font = self.res.font(config.FONT_BOLD, config.FONT_SIZE)
        self.t = 0.0
        self.queue = []                  # pending Events
        self.box = None                  # DialogueBox being shown
        self.after_queue = None          # callback when the queue empties
        self.mode = "msg"                # msg | cmd | skill | item | target
        self.commands = {}
        self.cmd_menu = MenuList(self.res, ["공격", "방어", "스킬", "아이템", "도망"],
                                 CMD_RECT, cancellable=True)
        self.sub = None
        self.prev_mode = "cmd"
        names = ", ".join(e.name for e in self.bs.enemies)
        self._show_text([f"{names}이(가) 나타났다!"], self._begin_input)
        self.res.music("battle")

    def _layout_enemies(self):
        n = len(self.bs.enemies)
        size = {1: 96, 2: 72}.get(n, 60)
        gap = 8
        x = (config.VIRTUAL_W - (n * size + (n - 1) * gap)) // 2
        self.enemy_img, self.enemy_pos = [], []
        for e in self.bs.enemies:
            try:
                img = pygame.transform.scale(self.res.image(MONSTER.format(e.data["sprite"])), (size, size))
            except FileNotFoundError:
                img = pygame.Surface((size, size), pygame.SRCALPHA)
                pygame.draw.ellipse(img, (160, 80, 200), img.get_rect())
            self.enemy_img.append(img)
            self.enemy_pos.append((x, 128 - size))
            x += size + gap

    def on_exit(self):
        self.res.stop_music()

    # --- event playback ---------------------------------------------
    def _show_text(self, lines, then=None):
        self.queue = [(lines, None)]
        self.after_queue = then
        self.mode = "msg"
        self._next_event()

    def _play_events(self, events, then):
        self.queue = [(e.lines, e) for e in events]
        self.after_queue = then
        self.mode = "msg"
        self._next_event()

    def _next_event(self):
        if not self.queue:
            self.box = None
            cb, self.after_queue = self.after_queue, None
            if cb:
                cb()
            return
        lines, ev = self.queue.pop(0)
        pages = [lines[i:i + 3] for i in range(0, len(lines), 3)] or [[""]]
        self.box = DialogueBox(self.res, pages, rect=INFO_RECT)
        if ev == "levelup":
            self.res.jingle("levelup")
        elif ev is not None:
            before = self.disp
            self.disp = ev.snap
            if ev.hit:
                self.shake[ev.hit] = 0.35
            if ev.sound:
                self.res.sfx({"miss": "buzzer"}.get(ev.sound, ev.sound))
            self._spawn_fx(ev)
            for i, hp in enumerate(self.disp[ENEMY]):
                if hp <= 0 < before[ENEMY][i]:
                    self.dying[i] = 0.0
                    self.res.sfx("defeat_enemy", 0.8)

    def target_pos(self, side, i):
        """Screen point where effects/popups for a combatant are drawn."""
        if side == ENEMY:
            (x, y), img = self.enemy_pos[i], self.enemy_img[i]
            return x + img.get_width() // 2, y + img.get_height() // 2
        return 272, 14 + i * 30

    def _spawn_fx(self, ev):
        if not ev.target:
            return
        side, i = ev.target
        pos = self.target_pos(side, i)
        if ev.fx:
            size = self.enemy_img[i].get_width() // 2 if side == ENEMY else 24
            self.fx.append(effects.make_fx(ev.fx, pos, size))
        if ev.amount:
            heal = ev.fx == "heal"
            color = effects.COLOR_HEAL if heal else effects.COLOR_CRIT if ev.crit else effects.COLOR_DAMAGE
            ppos = (pos[0], pos[1] - 10) if side == ENEMY else (pos[0] - 70, pos[1] + 4)
            self.fx.append(effects.Popup(ppos, str(ev.amount), self.popup_font, color))
        if ev.crit:
            self.fx.append(effects.Flash())
        if side == PARTY and not ev.fx == "heal":
            self.fx.append(effects.Flash((200, 0, 0), 0.15, 90))

    # --- command input ----------------------------------------------
    def _begin_input(self):
        self.commands = {}
        alive = self.bs.alive(PARTY)
        self.ci = alive[0]
        self.mode = "cmd"
        self.cmd_menu.index = 0

    def _next_member(self):
        later = [i for i in self.bs.alive(PARTY) if i > self.ci]
        if later:
            self.ci = later[0]
            self.mode = "cmd"
            self.cmd_menu.index = 0
        else:
            events = self.bs.run_round(self.commands)
            self._play_events(events, self._after_round)

    def _prev_member(self):
        earlier = [i for i in self.bs.alive(PARTY) if i < self.ci]
        if earlier:
            self.ci = earlier[-1]
            self.commands.pop(self.ci, None)

    def _choose_target(self, kind, make_action):
        """kind: enemy | ally | self | all_*; make_action(target) -> Action."""
        if kind in ("enemy", "ally"):
            side = ENEMY if kind == "enemy" else PARTY
            self.targets = self.bs.alive(side)
            self.target_side = side
            if len(self.targets) == 1:
                self._commit(make_action(self.targets[0]))
                return
            self.ti = 0 if side == ENEMY else self.targets.index(self.ci) if self.ci in self.targets else 0
            self.make_action = make_action
            self.prev_mode = self.mode
            self.mode = "target"
        else:
            self._commit(make_action(None))

    def _commit(self, action):
        self.commands[self.ci] = action
        self._next_member()

    def _update_cmd(self, dt):
        choice = self.cmd_menu.update(self.input, dt)
        if choice == -1:
            self._prev_member()
        elif choice == 0:
            self._choose_target("enemy", lambda t: Action("attack", t))
        elif choice == 1:
            self._commit(Action("defend"))
        elif choice == 2:
            char = self.bs.party[self.ci]
            sk = data_loader.skills()
            self.sub_ids = [sid for sid, _ in self.bs.usable_skills(char)]
            items = [(f"{sk[sid]['name']}", ok) for sid, ok in self.bs.usable_skills(char)]
            self.sub_costs = [f"{sk[sid]['mp']} MP" for sid in self.sub_ids]
            if items:
                self.sub = MenuList(self.res, items, INFO_RECT, rows=3)
                self.mode = "skill"
        elif choice == 3:
            it = data_loader.items()
            reserved = {}
            for a in self.commands.values():
                if a.kind == "item":
                    reserved[a.id] = reserved.get(a.id, 0) + 1
            usable = [(iid, q - reserved.get(iid, 0)) for iid, q in self.bs.usable_items()]
            self.sub_ids = [iid for iid, _ in usable]
            self.sub_costs = [f"x{q}" for _, q in usable]
            if usable:
                self.sub = MenuList(self.res, [(it[iid]["name"], q > 0) for iid, q in usable], INFO_RECT,
                                    rows=3)
                self.mode = "item"
            else:
                self.res.sfx("buzzer")
        elif choice == 4:
            self.commands = {i: Action("flee") for i in self.bs.alive(PARTY)}
            self._play_events(self.bs.run_round(self.commands), self._after_round)

    def _update_sub(self, dt):
        choice = self.sub.update(self.input, dt)
        if choice is None:
            return
        if choice == -1:
            self.mode = "cmd"
            return
        sid = self.sub_ids[choice]
        if self.mode == "skill":
            kind = data_loader.skills()[sid]["target"]
            self._choose_target(kind, lambda t: Action("skill", t, sid))
        else:
            self._choose_target("ally", lambda t: Action("item", t, sid))

    def _update_target(self, dt):
        inp = self.input
        n = len(self.targets)
        if inp.was_pressed("left") or inp.was_pressed("up"):
            self.ti = (self.ti - 1) % n
        elif inp.was_pressed("right") or inp.was_pressed("down"):
            self.ti = (self.ti + 1) % n
        elif inp.was_pressed("confirm"):
            self._commit(self.make_action(self.targets[self.ti]))
        elif inp.was_pressed("cancel"):
            self.mode = self.prev_mode

    # --- end of round -----------------------------------------------
    def _after_round(self):
        r = self.bs.result
        if r is None:
            self._begin_input()
        elif r == "victory":
            self.res.jingle("victory")
            lines = self.bs.apply_rewards()
            # level-up lines get their own page so the jingle lines up with the text
            normal = [l for l in lines if "레벨" not in l]
            ups = [l for l in lines if "레벨" in l]
            self.queue = [(normal, None)] + ([(ups, "levelup")] if ups else [])
            self.after_queue = self._leave
            self.mode = "msg"
            self._next_event()
        elif r == "fled":
            self._leave()
        else:
            self._show_text(["파티는 전멸했다..."], self._game_over)

    def _leave(self):
        self.engine.scenes.pop(fade=True)

    def _game_over(self):
        from scenes.game_over_scene import GameOverScene
        self.engine.scenes.change(GameOverScene(self.engine), fade=True)

    # --- frame ------------------------------------------------------
    def update(self, dt):
        self.t += dt
        self.fx = [f for f in self.fx if f.update(dt)]
        for i in list(self.dying):
            self.dying[i] += dt
        if self.intro:
            if not self.intro.update(dt):
                self.intro = None
            return
        for k in list(self.shake):
            self.shake[k] -= dt
            if self.shake[k] <= 0:
                del self.shake[k]
        if self.mode == "msg":
            if self.box and self.box.update(self.input, dt):
                self._next_event()
        elif self.mode == "cmd":
            self._update_cmd(dt)
        elif self.mode in ("skill", "item"):
            self._update_sub(dt)
        elif self.mode == "target":
            self._update_target(dt)

    def draw(self, surface):
        surface.blit(self.bg, (0, 0))
        self._draw_enemies(surface)
        self._draw_party(surface)
        if self.mode == "target":
            t = self.bs.side(self.target_side)[self.targets[self.ti]]
            draw_window(surface, (4, 4, 110, 22))
            draw_text(surface, self.font, t.name, (12, 8), config.COLOR_HIGHLIGHT)
        for f in self.fx:
            if not isinstance(f, effects.Flash):
                f.draw(surface)
        self.cmd_menu.draw(surface, active=self.mode == "cmd")
        if self.mode == "msg" and self.box:
            self.box.draw(surface)
        elif self.mode in ("skill", "item") or (self.mode == "target" and self.prev_mode != "cmd"):
            self._draw_sub(surface)
        else:
            draw_window(surface, INFO_RECT)
            if self.mode == "target":
                t = self.bs.side(self.target_side)[self.targets[self.ti]]
                draw_text(surface, self.font, f"대상: {t.name}", (96, 156))
            elif self.mode == "cmd":
                c = self.bs.party[self.ci]
                draw_text(surface, self.font, f"{c.name}은(는) 어떻게 할까?", (96, 156))
        for f in self.fx:
            if isinstance(f, effects.Flash):
                f.draw(surface)
        if self.intro:
            self.intro.draw(surface)

    def _draw_sub(self, surface):
        self.sub.draw(surface, active=self.mode in ("skill", "item"))
        x, y, w, _ = INFO_RECT
        for i in self.sub.visible():
            color = config.COLOR_TEXT if self.sub.items[i][1] else config.COLOR_TEXT_DIM
            draw_text(surface, self.font, self.sub_costs[i], (x + w - 16, self.sub.row_y(i)), color, align="right")
        sid = self.sub_ids[self.sub.index]
        table = data_loader.skills() if self.mode == "skill" or getattr(self, "prev_mode", "") == "skill" \
            else data_loader.items()
        draw_text(surface, self.small, table[sid].get("description", ""), (x + 8, y + 72),
                  config.COLOR_TEXT_DIM)

    def _draw_enemies(self, surface):
        hp = self.disp[ENEMY]
        for i, (img, (x, y)) in enumerate(zip(self.enemy_img, self.enemy_pos)):
            fade = self.dying.get(i)
            if hp[i] <= 0 and (fade is None or fade > 0.5):
                continue
            ox = 0
            if (ENEMY, i) in self.shake:
                ox = int(math.sin(self.shake[(ENEMY, i)] * 60) * 3)
                if int(self.t * 20) % 2:
                    continue   # blink on hit
            oy = int(math.sin(self.t * 2 + i) * 2)
            if fade is not None:
                img = img.copy()
                img.fill((255, 64, 64, 0), special_flags=pygame.BLEND_RGBA_ADD)
                img.set_alpha(int(255 * (1 - fade / 0.5)))
            surface.blit(img, (x + ox, y + oy))
            if self.mode == "target" and self.target_side == ENEMY and self.targets[self.ti] == i:
                draw_cursor(surface, (x + img.get_width() // 2 - 3, y - 10), self.t)

    def _draw_party(self, surface):
        n = len(self.bs.party)
        h = 10 + n * 30
        x0 = 230
        ox = int(math.sin(self.t * 80) * 2) if any(k[0] == PARTY for k in self.shake) else 0
        draw_window(surface, (x0 + ox, 4, 86, h))
        for i, c in enumerate(self.bs.party):
            hp, mp = self.disp[PARTY][i]
            y = 8 + i * 30
            active = self.mode != "msg" and i == self.ci
            color = config.COLOR_HIGHLIGHT if active else config.COLOR_TEXT
            if hp <= 0:
                color = config.COLOR_TEXT_DIM
            draw_text(surface, self.small, c.name, (x0 + 8 + ox, y), color)
            hp_color = COLOR_LOW if hp <= c.max_hp // 4 else config.COLOR_TEXT
            draw_text(surface, self.small, f"HP {hp:>3}/{c.max_hp}", (x0 + 8 + ox, y + 10), hp_color)
            draw_text(surface, self.small, f"MP {mp:>3}", (x0 + 8 + ox, y + 19), config.COLOR_TEXT_DIM)
            if self.mode == "target" and self.target_side == PARTY and self.targets[self.ti] == i:
                draw_cursor(surface, (x0 - 6, y + 4), self.t)
