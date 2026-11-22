"""Field exploration on Tiled maps: movement, collision, NPCs, signs, chests,
warps between maps and random encounters on tall-grass tiles."""
import random

import pygame

import config
from engine.scene import Scene
from gui.dialogue_box import DialogueBox
from gui.window import draw_text, draw_window
from systems import data_loader
from systems.field_map import FieldMap

T = config.TILE
CHAR_SHEET = "characters/devurandom_16x16/rpg_16x16_0.png"
DUNGEON_SHEET = "maps/kenney_tiny_dungeon/Tilemap/tilemap_packed.png"
CHEST_CLOSED, CHEST_OPEN = 89, 91
DIR_VEC = {"down": (0, 1), "left": (-1, 0), "right": (1, 0), "up": (0, -1)}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}


def load_frames(res, char_index=0):
    """devurandom sheet: 8 characters (4 per row), each in a 4x4 block of 16px
    cells. Only 3 rows are used: 0 = front (down), 1 = side facing left,
    2 = back (up); 3 walk frames each. Right is the left row mirrored."""
    sheet = res.image(CHAR_SHEET)
    ox, oy = (char_index % 4) * 4 * T, (char_index // 4) * 4 * T

    def row(r):
        return [sheet.subsurface((ox + f * T, oy + r * T, T, T)) for f in range(3)]

    left = row(1)
    return {"down": row(0), "left": left, "up": row(2),
            "right": [pygame.transform.flip(f, True, False) for f in left]}


def sheet_tile(res, rel, index, columns=12):
    sheet = res.image(rel)
    return sheet.subsurface(((index % columns) * T, (index // columns) * T, T, T))


class Actor:
    SPEED = 64  # px/sec

    def __init__(self, frames, gx, gy, facing="down"):
        self.frames = frames
        self.gx, self.gy = gx, gy
        self.px, self.py = gx * T, gy * T
        self.facing = facing
        self.moving = False
        self.anim = 0.0

    def place(self, gx, gy, facing=None):
        self.gx, self.gy = gx, gy
        self.px, self.py = gx * T, gy * T
        self.facing = facing or self.facing

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


class Npc(Actor):
    def __init__(self, res, obj):
        super().__init__(load_frames(res, obj.props.get("sprite", 2)), obj.x, obj.y,
                         obj.props.get("facing", "down"))
        self.obj = obj
        self.home_facing = self.facing
        self.home = (obj.x, obj.y)
        self.wander = obj.props.get("wander", 0)   # tiles from home it may stroll; 0 = stands still
        self.idle = random.uniform(1.0, 3.0)
        self.talking = False

    def think(self, dt, blocked):
        """Random stroll inside the wander radius. Returns nothing; moves itself."""
        if not self.wander or self.moving or self.talking:
            return
        self.idle -= dt
        if self.idle > 0:
            return
        self.idle = random.uniform(1.2, 3.5)
        d = random.choice(list(DIR_VEC))
        dx, dy = DIR_VEC[d]
        nx, ny = self.gx + dx, self.gy + dy
        if abs(nx - self.home[0]) > self.wander or abs(ny - self.home[1]) > self.wander:
            self.facing = d
            return
        self.try_move(d, blocked)


class WorldScene(Scene):
    BANNER_TIME = 2.0

    def on_enter(self):
        st = self.engine.state
        if st is None:  # scene opened directly (debug): start a fresh game
            from engine.state_manager import GameState
            st = self.engine.state = GameState.new_game()
        self.state = st
        self.map = FieldMap(st.map, images=True)
        self.npcs = [Npc(self.res, o) for o in self.map.objects_of("npc")]
        self.chests = self.map.objects_of("chest")
        self.chest_img = {False: sheet_tile(self.res, DUNGEON_SHEET, CHEST_CLOSED),
                          True: sheet_tile(self.res, DUNGEON_SHEET, CHEST_OPEN)}
        x, y = st.x, st.y
        if self.blocked(x, y):            # stale save / edited map: fall back to the map start
            x, y = self.map.start
        self.player = Actor(load_frames(self.res, 0), x, y, st.facing)
        self._sync_state()
        self.dialogue = None
        self.after_dialogue = None
        self.steps_to_encounter = self._roll_encounter()
        self.font = self.res.font(config.FONT_MAIN, config.FONT_SIZE)
        self.small = self.res.font(config.FONT_SMALL, config.FONT_SIZE_SMALL)
        self.banner = self.BANNER_TIME
        self._step_snd = 0
        self.res.music(self.map.bgm)

    def _sync_state(self):
        p = self.player
        self.state.x, self.state.y, self.state.facing = p.gx, p.gy, p.facing

    def on_pause(self):
        self._sync_state()

    def on_resume(self):
        self.res.music(self.map.bgm)
        self.steps_to_encounter = self._roll_encounter()

    @staticmethod
    def _roll_encounter():
        return random.randint(8, 20)

    def chest_opened(self, chest):
        return f"chest:{self.map.id}:{chest.name}" in self.state.flags

    def blocked(self, x, y, ignore=None):
        if self.map.solid(x, y):
            return True
        if self.map.object_at(x, y, ("warp",)) and ignore is not None:
            return True   # NPCs never wander onto warps
        if any((n.gx, n.gy) == (x, y) for n in self.npcs if n is not ignore):
            return True
        return any((c.x, c.y) == (x, y) for c in self.chests)

    # --- frame ------------------------------------------------------
    def update(self, dt):
        self.banner = max(0.0, self.banner - dt)
        if self.dialogue:
            if self.dialogue.update(self.input, dt):
                self.dialogue = None
                cb, self.after_dialogue = self.after_dialogue, None
                if cb:
                    cb()
                else:
                    self._release_npcs()
            return

        for n in self.npcs:
            n.update(dt)
            n.think(dt, lambda x, y, me=n: self.blocked(x, y, ignore=me) or (x, y) == (self.player.gx, self.player.gy))
        p = self.player
        if p.update(dt):
            self._on_step()
            return  # a warp or encounter may have started
        if p.moving or self.engine.scenes.busy:
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
        self._sync_state()
        self.res.sfx("step", 0.35)
        warp = self.map.object_at(p.gx, p.gy, ("warp",))
        if warp:
            self._warp(warp.props)
            return
        if self.map.encounter_tile(p.gx, p.gy) and self.map.encounters:
            self.steps_to_encounter -= 1
            if self.steps_to_encounter <= 0:
                from scenes.battle_scene import BattleScene
                self.engine.scenes.push(BattleScene(self.engine), fade=True)

    def _warp(self, props):
        st = self.state
        st.map, st.x, st.y = props["to_map"], props["to_x"], props["to_y"]
        st.facing = props.get("facing", self.player.facing)
        self.res.sfx("warp", 0.7)
        self.engine.scenes.change(WorldScene(self.engine), fade=True)

    def _say(self, pages, speaker=None, then=None):
        self.dialogue = DialogueBox(self.res, pages, speaker=speaker)
        self.after_dialogue = then

    def _interact(self):
        p = self.player
        dx, dy = DIR_VEC[p.facing]
        tx, ty = p.gx + dx, p.gy + dy
        for n in self.npcs:
            if (n.gx, n.gy) == (tx, ty) and not n.moving:
                n.facing = OPPOSITE[p.facing]
                n.talking = True
                then = self._inn if n.obj.props.get("action") == "inn" else None
                self._say(n.obj.props.get("dialogue") or ["..."], n.obj.name, then)
                return
        for c in self.chests:
            if (c.x, c.y) == (tx, ty):
                self._open_chest(c)
                return
        sign = self.map.object_at(tx, ty, ("sign",))
        if sign:
            self._say(sign.props.get("dialogue") or ["..."])

    def _open_chest(self, chest):
        if self.chest_opened(chest):
            self._say(["상자는 비어 있다."])
            return
        item, qty = chest.props["item"], chest.props.get("qty", 1)
        self.state.add_item(item, qty)
        self.state.flags.add(f"chest:{self.map.id}:{chest.name}")
        self.res.sfx("chest")
        name = data_loader.items()[item]["name"]
        self._say([f"상자를 열었다! {name}" + (f" x{qty}" if qty > 1 else "") + "을(를) 손에 넣었다."])

    def _inn(self):
        for c in self.state.party:
            c.hp, c.mp = c.max_hp, c.max_mp
        self.res.sfx("heal")
        self._say(["푹 쉬었다. HP와 MP가 모두 회복되었다!"])

    def _release_npcs(self):
        for n in self.npcs:
            if n.talking and not n.wander:
                n.facing = n.home_facing
            n.talking = False

    # --- drawing ----------------------------------------------------
    def camera(self):
        mw, mh = self.map.w * T, self.map.h * T
        cx = self.player.px + T / 2 - config.VIRTUAL_W / 2
        cy = self.player.py + T / 2 - config.VIRTUAL_H / 2
        cx = (mw - config.VIRTUAL_W) / 2 if mw <= config.VIRTUAL_W else max(0, min(cx, mw - config.VIRTUAL_W))
        cy = (mh - config.VIRTUAL_H) / 2 if mh <= config.VIRTUAL_H else max(0, min(cy, mh - config.VIRTUAL_H))
        return int(cx), int(cy)

    def draw(self, surface):
        cam = self.camera()
        surface.blit(self.map.surface, (-cam[0], -cam[1]))
        for c in self.chests:
            surface.blit(self.chest_img[self.chest_opened(c)], (c.x * T - cam[0], c.y * T - cam[1]))
        for a in sorted(self.npcs + [self.player], key=lambda a: a.py):
            a.draw(surface, cam)
        if self.banner > 0:
            w = self.font.size(self.map.name)[0] + 24
            draw_window(surface, ((config.VIRTUAL_W - w) // 2, 8, w, 22))
            draw_text(surface, self.font, self.map.name, (config.VIRTUAL_W // 2, 12), align="center")
        elif not self.dialogue:
            hint = "방향키: 이동  Z: 조사  C: 메뉴"
            draw_window(surface, (2, 220, self.small.size(hint)[0] + 12, 18))
            draw_text(surface, self.small, hint, (8, 223), config.COLOR_TEXT_DIM)
        if self.dialogue:
            self.dialogue.draw(surface)
