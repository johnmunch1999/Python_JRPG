"""Vertical selection list with cursor, inside a window. Scrolls when the
items do not fit."""
import pygame

import config
from gui.window import draw_cursor, draw_text, draw_window


class MenuList:
    """Items are (label, enabled) or plain strings.

    update() returns the selected index on confirm, -1 on cancel, else None.
    `rows` limits how many items are visible (default: as many as fit the rect).
    """

    LINE_H = 16

    def __init__(self, res, items, rect, cancellable=True, rows=None):
        self.res = res
        self.items = [(i, True) if isinstance(i, str) else i for i in items]
        self.rect = rect
        self.index = 0
        self.top = 0            # first visible item
        self._rows = rows
        self.cancellable = cancellable
        self.font = res.font(config.FONT_MAIN, config.FONT_SIZE)
        self.t = 0.0

    @property
    def rows(self):
        return self._rows or max(1, (self.rect[3] - 6) // self.LINE_H)

    def visible(self):
        """Indices of the items currently on screen, top to bottom."""
        return range(self.top, min(len(self.items), self.top + self.rows))

    def row_y(self, i):
        """Screen y of item i's text (only meaningful while it is visible)."""
        return self.rect[1] + 6 + (i - self.top) * self.LINE_H

    def _scroll_to_cursor(self):
        if self.index < self.top:
            self.top = self.index
        elif self.index >= self.top + self.rows:
            self.top = self.index - self.rows + 1
        self.top = max(0, min(self.top, max(0, len(self.items) - self.rows)))

    def update(self, inp, dt):
        self.t += dt
        n = len(self.items)
        if inp.was_pressed("up"):
            self.index = (self.index - 1) % n
            self.res.sfx("cursor", 0.6)
        elif inp.was_pressed("down"):
            self.index = (self.index + 1) % n
            self.res.sfx("cursor", 0.6)
        elif inp.was_pressed("confirm"):
            if self.items[self.index][1]:
                self.res.sfx("ok")
                return self.index
        elif inp.was_pressed("cancel") and self.cancellable:
            self.res.sfx("cancel")
            return -1
        self._scroll_to_cursor()
        return None

    def draw(self, surface, active=True):
        self._scroll_to_cursor()   # index may have been set directly
        draw_window(surface, self.rect)
        x = self.rect[0] + 18
        for i in self.visible():
            label, enabled = self.items[i]
            color = config.COLOR_TEXT if enabled else config.COLOR_TEXT_DIM
            draw_text(surface, self.font, label, (x, self.row_y(i)), color)
        if active:
            draw_cursor(surface, (x - 11, self.row_y(self.index) + 3), self.t)
        # scroll arrows
        rx, ry, rw, rh = self.rect
        cx = rx + rw - 8
        bob = int(self.t * 3) % 2
        if self.top > 0:
            pygame.draw.polygon(surface, config.COLOR_TEXT, [(cx - 3, ry + 6 - bob), (cx + 3, ry + 6 - bob),
                                                              (cx, ry + 2 - bob)])
        if self.top + self.rows < len(self.items):
            by = ry + rh - 6 + bob
            pygame.draw.polygon(surface, config.COLOR_TEXT, [(cx - 3, by), (cx + 3, by), (cx, by + 4)])
