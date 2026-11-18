"""Placeholder field: grid movement, collision, an NPC and random encounters.

The map is a hard-coded string for stage 1; stage 4 replaces it with Tiled/PyTMX.
"""
import random

import pygame

import config
from engine.scene import Scene
from gui.dialogue_box import DialogueBox
from gui.window import draw_text

T = config.TILE
CHAR_SHEET = "characters/devurandom_16x16/rpg_16x16_0.png"
SND_STEP = "sounds/kenney_rpg_audio/OGG/footstep0{}.ogg"

# '#' wall, '~' water, '.' grass, ',' tall grass (encounters), 'N' npc, 'P' start
MAP = [
    "####################",
    "#..................#",
    "#..P.......~~~~....#",
    "#..........~~~~....#",
    "#...N..............#",
    "#.......#####......#",
    "#.......#...#......#",
    "#..,,,,,,,,,,,,,...#",
    "#..,,,,,,,,,,,,,...#",
    "#..,,,,,,,,,,,,,...#",
    "#..................#",
    "#..................#",
    "#..................#",
    "#..................#",
    "####################",
]
TILE_COLORS = {
    "#": (88, 72, 64), ".": (72, 152, 72), ",": (40, 112, 48), "~": (48, 96, 200),
}
SOLID = {"#", "~"}
DIR_VEC = {"down": (0, 1), "left": (-1, 0), "right": (1, 0), "up": (0, -1)}
DIR_ROW = {"down": 0, "left": 1, "right": 2, "up": 3}


def load_frames(res, char_index=0):
    """devurandom sheet: 4 characters per row, each a 4x4 block of 16px cells
    (3 walk frames per direction)."""
    sheet = res.image(CHAR_SHEET)
    ox, oy = (char_index % 4) * 4 * T, (char_index // 4) * 4 * T
    return {d: [sheet.subsurface((ox + f * T, oy + row * T, T, T)) for f in range(3)]
            for d, row in DIR_ROW.items()}


class Actor:
    SPEED = 64  # px/sec

    def __init__(self, frames, gx, gy, facing="down"):
        self.frames = frames
        self.gx, self.gy = gx, gy
        self.px, self.py = gx * T, gy * T
        self.facing = facing
        self.moving = False
        self.anim = 0.0

    def try_move(self, d, blocked):
        self.facing = d
        dx, dy = DIR_VEC[d]
        nx, ny = self.gx + dx, self.gy + dy
        if blocked(nx, ny):
            return False
        self.gx, self.gy = nx, ny
        self.moving = True
        return True

    def update(self, dt):
        """Returns True on the frame a step finishes."""
        if not self.moving:
            self.anim = 0
            return False
        self.anim += dt
        tx, ty = self.gx * T, self.gy * T
        step = self.SPEED * dt
        self.px += max(-step, min(step, tx - self.px))
        self.py += max(-step, min(step, ty - self.py))
        if (self.px, self.py) == (tx, ty):
            self.moving = False
            return True
        return False

    def draw(self, surface, cam):
        frame = (1, 0, 1, 2)[int(self.anim * 8) % 4] if self.moving else 1
        surface.blit(self.frames[self.facing][frame],
                     (round(self.px - cam[0]), round(self.py - cam[1])))


class WorldScene(Scene):
    def on_enter(self):
        self.grid = [list(row) for row in MAP]
        self.w, self.h = len(self.grid[0]), len(self.grid)
        self.player = self.npc = None
        for y, row in enumerate(self.grid):
            for x, c in enumerate(row):
                if c == "P":
                    self.player = Actor(load_frames(self.res, 0), x, y)
                    row[x] = "."
                elif c == "N":
                    self.npc = Actor(load_frames(self.res, 2), x, y, "right")
                    row[x] = "."
        self.dialogue = None
        self.steps_to_encounter = self._roll_encounter()
        self.font = self.res.font(config.FONT_SMALL, config.FONT_SIZE_SMALL)
        self._step_snd = 0
        self.res.stop_music()

    def on_resume(self):
        self.steps_to_encounter = self._roll_encounter()

    @staticmethod
    def _roll_encounter():
        return random.randint(8, 20)

    def blocked(self, x, y):
        if not (0 <= x < self.w and 0 <= y < self.h):
            return True
        if self.grid[y][x] in SOLID:
            return True
        return self.npc is not None and (self.npc.gx, self.npc.gy) == (x, y)

    def update(self, dt):
        if self.dialogue:
            if self.dialogue.update(self.input, dt):
                self.dialogue = None
            return

        p = self.player
        if p.update(dt):
            self._on_step()
            return  # encounter may have started
        if p.moving:
            return

        if self.input.was_pressed("menu") or self.input.was_pressed("cancel"):
            from scenes.menu_scene import MenuScene
            self.engine.scenes.push(MenuScene(self.engine))
            return
        if self.input.was_pressed("confirm"):
            self._interact()
            return
        d = self.input.direction()
        if d:
            p.try_move(d, self.blocked)

    def _on_step(self):
        p = self.player
        self._step_snd = (self._step_snd + 1) % 10
        self.res.play(SND_STEP.format(self._step_snd), 0.25)
        if self.grid[p.gy][p.gx] == ",":
            self.steps_to_encounter -= 1
            if self.steps_to_encounter <= 0:
                from scenes.battle_scene import BattleScene
                self.engine.scenes.push(BattleScene(self.engine), fade=True)

    def _interact(self):
        p = self.player
        dx, dy = DIR_VEC[p.facing]
        if self.npc and (p.gx + dx, p.gy + dy) == (self.npc.gx, self.npc.gy):
            self.npc.facing = {"up": "down", "down": "up", "left": "right", "right": "left"}[p.facing]
            self.dialogue = DialogueBox(self.res, [
                ["어서 오게, 여행자여.", "이 마을 남쪽 풀숲에는 몬스터가 나온다네."],
                ["C 또는 Tab 키로 메뉴를 열 수 있지.", "조심해서 다녀오게!"],
            ], speaker="촌장")

    def camera(self):
        cx = self.player.px + T / 2 - config.VIRTUAL_W / 2
        cy = self.player.py + T / 2 - config.VIRTUAL_H / 2
        cx = max(0, min(cx, self.w * T - config.VIRTUAL_W))
        cy = max(0, min(cy, self.h * T - config.VIRTUAL_H))
        return int(cx), int(cy)

    def draw(self, surface):
        cam = self.camera()
        for y, row in enumerate(self.grid):
            for x, c in enumerate(row):
                r = pygame.Rect(x * T - cam[0], y * T - cam[1], T, T)
                pygame.draw.rect(surface, TILE_COLORS[c], r)
                if c == "#":
                    pygame.draw.rect(surface, (56, 44, 40), r, 1)
                elif c == ",":
                    pygame.draw.line(surface, (24, 80, 32), (r.x + 4, r.y + 12), (r.x + 6, r.y + 6))
                    pygame.draw.line(surface, (24, 80, 32), (r.x + 10, r.y + 12), (r.x + 12, r.y + 7))
        actors = sorted([a for a in (self.npc, self.player) if a], key=lambda a: a.py)
        for a in actors:
            a.draw(surface, cam)
        draw_text(surface, self.font, "방향키: 이동  Z: 대화  C: 메뉴", (4, 4), config.COLOR_TEXT_DIM)
        if self.dialogue:
            self.dialogue.draw(surface)
