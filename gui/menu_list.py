"""Vertical selection list with cursor, inside a window."""
import config
from gui.window import draw_cursor, draw_text, draw_window

SND_MOVE = "sounds/kenney_rpg_audio/OGG/cloth1.ogg"
SND_OK = "sounds/kenney_rpg_audio/OGG/metalClick.ogg"
SND_CANCEL = "sounds/kenney_rpg_audio/OGG/bookClose.ogg"


class MenuList:
    """Items are (label, enabled) or plain strings.

    update() returns the selected index on confirm, -1 on cancel, else None.
    """

    LINE_H = 16

    def __init__(self, res, items, rect, cancellable=True):
        self.res = res
        self.items = [(i, True) if isinstance(i, str) else i for i in items]
        self.rect = rect
        self.index = 0
        self.cancellable = cancellable
        self.font = res.font(config.FONT_MAIN, config.FONT_SIZE)
        self.t = 0.0

    def update(self, inp, dt):
        self.t += dt
        n = len(self.items)
        if inp.was_pressed("up"):
            self.index = (self.index - 1) % n
            self.res.play(SND_MOVE, 0.4)
        elif inp.was_pressed("down"):
            self.index = (self.index + 1) % n
            self.res.play(SND_MOVE, 0.4)
        elif inp.was_pressed("confirm"):
            if self.items[self.index][1]:
                self.res.play(SND_OK)
                return self.index
        elif inp.was_pressed("cancel") and self.cancellable:
            self.res.play(SND_CANCEL)
            return -1
        return None

    def draw(self, surface, active=True):
        draw_window(surface, self.rect)
        x, y = self.rect[0] + 18, self.rect[1] + 6
        for i, (label, enabled) in enumerate(self.items):
            color = config.COLOR_TEXT if enabled else config.COLOR_TEXT_DIM
            draw_text(surface, self.font, label, (x, y + i * self.LINE_H), color)
        if active:
            draw_cursor(surface, (x - 11, y + self.index * self.LINE_H + 3), self.t)
