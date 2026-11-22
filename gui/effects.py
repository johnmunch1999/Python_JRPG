"""Short-lived visual effects (battle hits, heals, popups, screen flashes).

Each effect has update(dt) -> bool (False when finished) and draw(surface).
"""
import math
import random

import pygame

COLOR_DAMAGE = (255, 255, 255)
COLOR_CRIT = (255, 224, 96)
COLOR_HEAL = (120, 240, 140)


class Effect:
    DURATION = 0.5

    def __init__(self, pos):
        self.x, self.y = pos
        self.t = 0.0

    @property
    def p(self):
        return min(1.0, self.t / self.DURATION)

    def update(self, dt):
        self.t += dt
        return self.t < self.DURATION

    def draw(self, surface):
        pass


class Popup(Effect):
    """Bouncing damage / heal number."""
    DURATION = 0.9

    def __init__(self, pos, text, font, color):
        super().__init__(pos)
        self.img = font.render(text, False, color)
        self.shadow = font.render(text, False, (0, 0, 0))

    def draw(self, surface):
        t = self.t
        # one bounce over the first 0.35 s, then hold and fade
        hop = abs(math.sin(min(t, 0.35) / 0.35 * math.pi)) * 10 if t < 0.35 else 0
        y = self.y - 6 - hop - max(0, t - 0.6) * 20
        x = self.x - self.img.get_width() // 2
        alpha = 255 if t < 0.6 else int(255 * (1 - (t - 0.6) / 0.3))
        for img, off in ((self.shadow, 1), (self.img, 0)):
            img.set_alpha(max(0, alpha))
            surface.blit(img, (x + off, int(y) + off))


class Slash(Effect):
    """Three diagonal strokes that sweep across the target."""
    DURATION = 0.28

    def __init__(self, pos, size=40, color=(255, 255, 255)):
        super().__init__(pos)
        self.size = size
        self.color = color

    def draw(self, surface):
        s = self.size
        for k, off in enumerate((-8, 0, 8)):
            local = min(1.0, max(0.0, self.p * 1.6 - k * 0.2))
            if local <= 0:
                continue
            x0, y0 = self.x - s // 2 + off, self.y - s // 2
            x1, y1 = x0 + s * local, y0 + s * local
            width = 3 if local < 0.8 else 1
            pygame.draw.line(surface, self.color, (x0, y0), (x1, y1), width)


class Sparkles(Effect):
    """Rising green sparkles for healing."""
    DURATION = 0.7

    def __init__(self, pos, color=COLOR_HEAL):
        super().__init__(pos)
        rng = random.Random(int(pos[0] * 31 + pos[1]))
        self.parts = [(rng.uniform(-16, 16), rng.uniform(0, 16), rng.uniform(0, 0.3)) for _ in range(10)]
        self.color = color

    def draw(self, surface):
        for dx, dy, delay in self.parts:
            lt = self.t - delay
            if lt < 0 or lt > 0.4:
                continue
            x = int(self.x + dx)
            y = int(self.y + dy - lt * 60)
            r = 2 if lt < 0.25 else 1
            pygame.draw.line(surface, self.color, (x - r, y), (x + r, y))
            pygame.draw.line(surface, self.color, (x, y - r), (x, y + r))


class Rings(Effect):
    """Expanding sound-wave rings."""
    DURATION = 0.45

    def __init__(self, pos, color=(200, 180, 255)):
        super().__init__(pos)
        self.color = color

    def draw(self, surface):
        for k in range(3):
            local = self.p * 1.5 - k * 0.25
            if 0 < local < 1:
                pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(4 + local * 28), 1)


class Flash(Effect):
    """Full-screen colour flash (critical hits, battle start)."""

    def __init__(self, color=(255, 255, 255), duration=0.12, strength=180):
        super().__init__((0, 0))
        self.color = color
        self.DURATION = duration
        self.strength = strength

    def draw(self, surface):
        veil = pygame.Surface(surface.get_size())
        veil.fill(self.color)
        veil.set_alpha(int(self.strength * (1 - self.p)))
        surface.blit(veil, (0, 0))


def make_fx(name, pos, size=40):
    """Effect for a skills.json "fx" value."""
    if name == "heal":
        return Sparkles(pos)
    if name == "wave":
        return Rings(pos)
    return Slash(pos, size)


class BattleIntro:
    """Classic encounter wipe: black bars slide away from the centre."""
    DURATION = 0.6

    def __init__(self):
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        return self.t < self.DURATION

    def draw(self, surface):
        w, h = surface.get_size()
        p = min(1.0, self.t / self.DURATION)
        bars = 12
        bh = h // bars + 1
        for i in range(bars):
            # alternate bars leave to the left / right with a small stagger
            local = max(0.0, min(1.0, p * 1.4 - (i % 4) * 0.1))
            cover = int(w * (1 - local))
            x = 0 if i % 2 == 0 else w - cover
            pygame.draw.rect(surface, (0, 0, 0), (x, i * bh, cover, bh))
