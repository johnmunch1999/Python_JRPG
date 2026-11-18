"""Typewriter-style message box with paging."""
import config
from gui.window import draw_cursor, draw_text, draw_window

SND_NEXT = "sounds/kenney_rpg_audio/OGG/bookFlip1.ogg"


class DialogueBox:
    CHARS_PER_SEC = 40
    LINE_H = 15

    def __init__(self, res, pages, rect=(4, 172, 312, 64), speaker=None):
        self.res = res
        self.pages = [p if isinstance(p, list) else [p] for p in pages]
        self.rect = rect
        self.speaker = speaker
        self.font = res.font(config.FONT_MAIN, config.FONT_SIZE)
        self.page = 0
        self.shown = 0.0
        self.t = 0.0
        self.finished = False

    def _page_len(self):
        return sum(len(line) for line in self.pages[self.page])

    @property
    def page_done(self):
        return self.shown >= self._page_len()

    def update(self, inp, dt):
        """Returns True once the last page is dismissed."""
        if self.finished:
            return True
        self.t += dt
        self.shown = min(self.shown + self.CHARS_PER_SEC * dt, self._page_len())
        if inp.was_pressed("confirm") or inp.was_pressed("cancel"):
            if not self.page_done:
                self.shown = self._page_len()          # skip typing
            elif self.page + 1 < len(self.pages):
                self.page += 1
                self.shown = 0
                self.res.play(SND_NEXT, 0.4)
            else:
                self.finished = True
        return self.finished

    def draw(self, surface):
        draw_window(surface, self.rect)
        x, y = self.rect[0] + 8, self.rect[1] + 6
        if self.speaker:
            draw_text(surface, self.font, self.speaker, (x, y), config.COLOR_HIGHLIGHT)
            y += self.LINE_H
        remaining = int(self.shown)
        for line in self.pages[self.page]:
            draw_text(surface, self.font, line[:remaining], (x, y))
            remaining -= len(line)
            if remaining <= 0:
                break
            y += self.LINE_H
        if self.page_done:
            rx = self.rect[0] + self.rect[2] - 12
            ry = self.rect[1] + self.rect[3] - 12
            draw_cursor(surface, (rx, ry), self.t)
