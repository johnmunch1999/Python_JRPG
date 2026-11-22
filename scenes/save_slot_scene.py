"""Slot picker overlay used for both saving (field menu) and loading (title)."""
import sqlite3

import config
from engine.scene import Scene
from gui.dialogue_box import DialogueBox
from gui.menu_list import MenuList
from gui.window import draw_text, draw_window
from systems import data_loader


def _fmt_time(sec):
    sec = int(sec)
    return f"{sec // 3600:02d}:{sec // 60 % 60:02d}:{sec % 60:02d}"


class SaveSlotScene(Scene):
    transparent = True
    RECT = (40, 40, 240, 126)

    def __init__(self, engine, mode):
        super().__init__(engine)
        assert mode in ("save", "load")
        self.mode = mode

    def on_enter(self):
        self.font = self.res.font(config.FONT_MAIN, config.FONT_SIZE)
        self.small = self.res.font(config.FONT_SMALL, config.FONT_SIZE_SMALL)
        self.message = None
        self._refresh()

    def _refresh(self):
        self.slots = self.engine.saves.list_slots()
        items = []
        for n in range(1, config.SAVE_SLOTS + 1):
            enabled = self.mode == "save" or n in self.slots
            items.append((f"슬롯 {n}", enabled))
        old = getattr(self, "menu", None)
        self.menu = MenuList(self.res, items, (self.RECT[0], self.RECT[1] + 22, self.RECT[2], 104))
        self.menu.LINE_H = 32
        if old:
            self.menu.index = old.index
        elif self.engine.state and self.engine.state.slot:
            self.menu.index = self.engine.state.slot - 1
        elif self.mode == "load" and self.slots:
            self.menu.index = min(self.slots) - 1

    def update(self, dt):
        if self.message:
            if self.message.update(self.input, dt):
                self.message = None
                self.engine.scenes.pop()
            return
        choice = self.menu.update(self.input, dt)
        if choice == -1:
            self.engine.scenes.pop()
        elif choice is not None:
            slot = choice + 1
            if self.mode == "save":
                try:
                    self.engine.saves.save(slot, self.engine.state)
                except (sqlite3.Error, OSError):
                    self.res.sfx("buzzer")
                    self.message = DialogueBox(self.res, ["저장에 실패했습니다.", "디스크 공간이나 권한을 확인해 주세요."])
                    return
                self.res.sfx("save")
                self._refresh()
                self.message = DialogueBox(self.res, [f"슬롯 {slot}에 저장했습니다."])
            else:
                try:
                    state = self.engine.saves.load(slot)
                except (sqlite3.Error, KeyError, ValueError, RuntimeError):
                    self.res.sfx("buzzer")
                    self.message = DialogueBox(self.res, ["이 슬롯은 불러올 수 없습니다.",
                                                          "현재 게임 데이터와 맞지 않습니다."])
                    return
                self.engine.state = state
                from scenes.world_scene import WorldScene
                self.engine.scenes.change(WorldScene(self.engine))

    def draw(self, surface):
        x, y, w, _ = self.RECT
        draw_window(surface, (x, y, w, 22))
        draw_text(surface, self.font, "어디에 저장할까요?" if self.mode == "save" else "불러올 슬롯을 선택하세요.",
                  (x + 8, y + 4))
        self.menu.draw(surface, active=self.message is None)
        chars = data_loader.characters()
        for n in range(1, config.SAVE_SLOTS + 1):
            ty = y + 22 + 6 + (n - 1) * 32
            s = self.slots.get(n)
            if s:
                name = chars.get(s["char_id"], {}).get("name", "?")
                info = f"{name} Lv {s['level']}   {_fmt_time(s['playtime'])}"
                draw_text(surface, self.font, info, (x + 80, ty))
                draw_text(surface, self.small, s["saved_at"].replace("T", " "), (x + 80, ty + 14),
                          config.COLOR_TEXT_DIM)
            else:
                draw_text(surface, self.font, "- 비어 있음 -", (x + 80, ty), config.COLOR_TEXT_DIM)
        if self.message:
            self.message.draw(surface)
