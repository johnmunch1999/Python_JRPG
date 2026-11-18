"""Classic JRPG bordered window and text helpers."""
import pygame

import config


def draw_window(surface, rect, alpha=235):
    """Blue gradient panel with a white rounded double border."""
    rect = pygame.Rect(rect)
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    top, bot = config.COLOR_WINDOW_TOP, config.COLOR_WINDOW_BOTTOM
    h = max(rect.h - 1, 1)
    for y in range(rect.h):
        t = y / h
        color = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        pygame.draw.line(panel, (*color, alpha), (0, y), (rect.w, y))
    local = panel.get_rect()
    pygame.draw.rect(panel, (0, 0, 0, 255), local, 1, border_radius=3)
    pygame.draw.rect(panel, (*config.COLOR_BORDER, 255), local.inflate(-2, -2), 1, border_radius=3)
    # cut transparent corners outside the rounded border
    for cx, cy in ((0, 0), (local.w - 1, 0), (0, local.h - 1), (local.w - 1, local.h - 1)):
        panel.set_at((cx, cy), (0, 0, 0, 0))
    surface.blit(panel, rect.topleft)


def draw_text(surface, font, text, pos, color=None, shadow=True, align="left"):
    """Text with a 1px drop shadow (crisp, no anti-aliasing)."""
    color = color or config.COLOR_TEXT
    img = font.render(text, False, color)
    rect = img.get_rect()
    setattr(rect, {"left": "topleft", "center": "midtop", "right": "topright"}[align], pos)
    if shadow:
        surface.blit(font.render(text, False, (0, 0, 0)), rect.move(1, 1))
    surface.blit(img, rect)
    return rect


def draw_cursor(surface, pos, t):
    """Small bobbing right-pointing triangle cursor."""
    x, y = pos
    x += int(abs(((t * 4) % 2) - 1) * 2)  # gentle 2px bob
    pts = [(x, y), (x + 5, y + 4), (x, y + 8)]
    pygame.draw.polygon(surface, (0, 0, 0), [(px + 1, py + 1) for px, py in pts])
    pygame.draw.polygon(surface, config.COLOR_HIGHLIGHT, pts)
