"""Item / equipment / status screens opened from the field menu."""
import config
from engine.scene import Scene
from gui.dialogue_box import DialogueBox
from gui.menu_list import MenuList
from gui.window import draw_text, draw_window
from systems import data_loader

PANEL = (4, 4, 312, 232)
SLOTS = (("weapon", "무기"), ("armor", "갑옷"))
STAT_NAMES = (("hp", "최대 HP"), ("mp", "최대 MP"), ("atk", "공격"), ("def", "방어"), ("agi", "민첩"))
COLOR_UP, COLOR_DOWN = (120, 232, 120), (255, 120, 104)


class _Panel(Scene):
    transparent = False   # full-screen panel; nothing below needs drawing

    def on_enter(self):
        self.font = self.res.font(config.FONT_MAIN, config.FONT_SIZE)
        self.small = self.res.font(config.FONT_SMALL, config.FONT_SIZE_SMALL)
        self.state = self.engine.state
        self.ci = 0          # selected party member
        self.message = None

    @property
    def char(self):
        return self.state.party[self.ci]

    def _cycle_member(self):
        n = len(self.state.party)
        if self.input.was_pressed("left"):
            self.ci = (self.ci - 1) % n
            return True
        if self.input.was_pressed("right"):
            self.ci = (self.ci + 1) % n
            return True
        return False

    def _message_update(self, dt):
        if self.message and self.message.update(self.input, dt):
            self.message = None
        return self.message is not None

    def _header(self, surface, title):
        draw_window(surface, PANEL)
        draw_text(surface, self.font, title, (14, 9), config.COLOR_HIGHLIGHT)
        if len(self.state.party) > 1:
            draw_text(surface, self.small, "◀ ▶ 동료 전환", (306, 11), config.COLOR_TEXT_DIM, align="right")


# ----------------------------------------------------------------------
class ItemScene(_Panel):
    LIST_RECT = (10, 26, 300, 150)

    def on_enter(self):
        super().on_enter()
        self.picking = False   # choosing which member to use the item on
        self._build()

    def _build(self, keep=0):
        it = data_loader.items()
        self.ids = sorted(self.state.inventory, key=lambda i: (it[i]["type"] != "consumable", i))
        rows = [(it[i]["name"], it[i]["type"] == "consumable") for i in self.ids] or [("(비어 있음)", False)]
        self.menu = MenuList(self.res, rows, self.LIST_RECT)
        self.menu.index = min(keep, len(rows) - 1)

    def update(self, dt):
        if self._message_update(dt):
            return
        if self.picking:
            self._update_pick()
            return
        choice = self.menu.update(self.input, dt)
        if choice == -1:
            self.engine.scenes.pop()
        elif choice is not None and self.ids:
            if len(self.state.party) == 1:
                self._use(self.ids[choice], 0)
            else:
                self.picking, self.ci = True, 0

    def _update_pick(self):
        if self._cycle_member() or self.input.was_pressed("up") or self.input.was_pressed("down"):
            if self.input.was_pressed("up"):
                self.ci = (self.ci - 1) % len(self.state.party)
            elif self.input.was_pressed("down"):
                self.ci = (self.ci + 1) % len(self.state.party)
        elif self.input.was_pressed("confirm"):
            self.picking = False
            self._use(self.ids[self.menu.index], self.ci)
        elif self.input.was_pressed("cancel"):
            self.picking = False

    def _use(self, item_id, member):
        item = data_loader.items()[item_id]
        c = self.state.party[member]
        eff = item.get("effect", {})
        gain_hp = min(eff.get("hp", 0), c.max_hp - c.hp) if c.alive else 0
        gain_mp = min(eff.get("mp", 0), c.max_mp - c.mp) if c.alive else 0
        if gain_hp <= 0 and gain_mp <= 0:
            self.res.sfx("buzzer")
            self.message = DialogueBox(self.res, ["사용해도 효과가 없다."])
            return
        self.state.remove_item(item_id)
        c.hp += gain_hp
        c.mp += gain_mp
        parts = ([f"HP {gain_hp}"] if gain_hp else []) + ([f"MP {gain_mp}"] if gain_mp else [])
        self.res.sfx("heal")
        self.message = DialogueBox(self.res, [f"{c.name}의 {', '.join(parts)} 회복!"])
        self._build(self.menu.index)

    def draw(self, surface):
        self._header(surface, f"아이템            소지금 {self.state.gold} G")
        it = data_loader.items()
        self.menu.draw(surface, active=not self.picking and not self.message)
        x, y, w, _ = self.LIST_RECT
        for i in self.menu.visible() if self.ids else ():
            iid = self.ids[i]
            draw_text(surface, self.font, f"x{self.state.inventory[iid]}", (x + w - 16, self.menu.row_y(i)),
                      align="right")
        if self.ids:
            item = it[self.ids[self.menu.index]]
            kind = {"weapon": "무기", "armor": "갑옷"}.get(item["type"], "소모품")
            draw_text(surface, self.small, f"[{kind}] {item.get('description', '')}", (14, 182))
        for i, c in enumerate(self.state.party):
            color = config.COLOR_HIGHLIGHT if self.picking and i == self.ci else config.COLOR_TEXT
            draw_text(surface, self.small, f"{c.name}  HP {c.hp}/{c.max_hp}  MP {c.mp}/{c.max_mp}",
                      (14, 198 + i * 12), color)
        if self.message:
            self.message.draw(surface)


# ----------------------------------------------------------------------
class EquipScene(_Panel):
    SLOT_RECT = (10, 40, 150, 40)
    LIST_RECT = (164, 40, 146, 120)

    def on_enter(self):
        super().on_enter()
        self.slot_menu = None
        self.pick = None   # MenuList of candidates for the chosen slot
        self._build_slots()

    def _item_name(self, iid):
        return data_loader.items()[iid]["name"] if iid else "-"

    def _build_slots(self, keep=0):
        rows = [f"{label}  {self._item_name(getattr(self.char, key))}" for key, label in SLOTS]
        self.slot_menu = MenuList(self.res, rows, self.SLOT_RECT)
        self.slot_menu.index = keep

    def _candidates(self, slot):
        it = data_loader.items()
        ids = sorted(i for i in self.state.inventory if it[i]["type"] == slot)
        return ids + [None]   # None = unequip

    def update(self, dt):
        if self.pick:
            choice = self.pick.update(self.input, dt)
            if choice == -1:
                self.pick = None
            elif choice is not None:
                slot = SLOTS[self.slot_menu.index][0]
                self.state.equip(self.char, slot, self.cands[choice])
                self.res.sfx("equip")
                self.pick = None
                self._build_slots(self.slot_menu.index)
            return
        if self._cycle_member():
            self._build_slots()
            return
        choice = self.slot_menu.update(self.input, dt)
        if choice == -1:
            self.engine.scenes.pop()
        elif choice is not None:
            self.cands = self._candidates(SLOTS[choice][0])
            rows = [self._item_name(i) if i else "(장비 해제)" for i in self.cands]
            self.pick = MenuList(self.res, rows, self.LIST_RECT)

    def _preview(self):
        """Stats if the highlighted candidate were equipped (None when not picking)."""
        if not self.pick:
            return None
        c = self.char
        slot = SLOTS[self.slot_menu.index][0]
        old = getattr(c, slot)
        setattr(c, slot, self.cands[self.pick.index])
        stats = {k: c.stat(k) for k, _ in STAT_NAMES}
        setattr(c, slot, old)
        return stats

    def draw(self, surface):
        c = self.char
        self._header(surface, "장비")
        draw_text(surface, self.font, f"{c.name}   Lv {c.level}", (14, 24))
        self.slot_menu.draw(surface, active=self.pick is None)
        if self.pick:
            self.pick.draw(surface)
        preview = self._preview()
        y0 = 90
        draw_window(surface, (10, y0, 150, 82))
        for i, (key, label) in enumerate(STAT_NAMES):
            y = y0 + 6 + i * 14
            now = c.stat(key)
            draw_text(surface, self.small, label, (18, y))
            draw_text(surface, self.small, str(now), (100, y), align="right")
            if preview and preview[key] != now:
                new = preview[key]
                draw_text(surface, self.small, f"→ {new}", (108, y), COLOR_UP if new > now else COLOR_DOWN)
        if self.pick and self.cands[self.pick.index]:
            desc = data_loader.items()[self.cands[self.pick.index]].get("description", "")
            draw_text(surface, self.small, desc, (14, 180))
        draw_text(surface, self.small, "장비를 바꾸면 이전 장비는 가방으로 돌아갑니다.", (14, 214),
                  config.COLOR_TEXT_DIM)


# ----------------------------------------------------------------------
class StatusScene(_Panel):
    def update(self, dt):
        if self._cycle_member():
            return
        if self.input.was_pressed("cancel") or self.input.was_pressed("confirm") or self.input.was_pressed("menu"):
            self.engine.scenes.pop()

    def draw(self, surface):
        from entities.character import exp_to_next
        c = self.char
        sk = data_loader.skills()
        self._header(surface, "상태")
        draw_text(surface, self.font, f"{c.name}", (14, 28))
        draw_text(surface, self.font, f"Lv {c.level}", (120, 28))
        draw_text(surface, self.small, f"경험치 {c.exp} / 다음 레벨까지 {exp_to_next(c.level) - c.exp}", (14, 46),
                  config.COLOR_TEXT_DIM)
        draw_text(surface, self.font, f"HP {c.hp} / {c.max_hp}", (14, 64))
        draw_text(surface, self.font, f"MP {c.mp} / {c.max_mp}", (14, 80))
        for i, (key, label) in enumerate(STAT_NAMES[2:]):
            draw_text(surface, self.font, f"{label}  {c.stat(key)}", (14, 104 + i * 16))
        draw_text(surface, self.font, "장비", (160, 64), config.COLOR_HIGHLIGHT)
        for i, (key, label) in enumerate(SLOTS):
            iid = getattr(c, key)
            draw_text(surface, self.font, f"{label}  {data_loader.items()[iid]['name'] if iid else '-'}",
                      (160, 80 + i * 16))
        draw_text(surface, self.font, "스킬", (160, 124), config.COLOR_HIGHLIGHT)
        for i, sid in enumerate(c.skills):
            draw_text(surface, self.font, f"{sk[sid]['name']}  {sk[sid]['mp']} MP", (160, 140 + i * 16))
        draw_text(surface, self.small, f"플레이 시간 {int(self.state.playtime) // 60}분   소지금 {self.state.gold} G",
                  (14, 214), config.COLOR_TEXT_DIM)
