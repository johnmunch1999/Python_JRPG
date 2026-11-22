"""Tiled (.tmx) field maps loaded with PyTMX.

Layers: "ground" and "deco" tile layers (tile property solid=true blocks,
encounter=true enables random battles) and an "objects" object layer holding
npc / sign / chest / warp objects. Map properties: name, start_x, start_y,
encounters (JSON list of monster groups).
"""
import glob
import json
import os

import pytmx

import config

T = config.TILE
MAP_DIR = os.path.join(config.DATA_DIR, "maps")
_meta_cache = {}
NPC_SPRITES = 8          # characters in devurandom rpg_16x16_0.png (4 x 2 blocks)
FACINGS = ("up", "down", "left", "right")


def map_path(map_id):
    return os.path.join(MAP_DIR, map_id + ".tmx")


def all_map_ids():
    return sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(MAP_DIR, "*.tmx")))


def _json_prop(props, key, default):
    v = props.get(key)
    return json.loads(v) if isinstance(v, str) else (default if v is None else v)


class MapObject:
    def __init__(self, obj):
        self.type = obj.type
        self.name = obj.name
        self.x, self.y = int(obj.x) // T, int(obj.y) // T
        self.props = dict(obj.properties)
        if "dialogue" in self.props:
            self.props["dialogue"] = _json_prop(self.props, "dialogue", [])


class FieldMap:
    """Logic view of a map. Pass images=True (needs a display) to also build layer surfaces."""

    def __init__(self, map_id, images=False):
        self.id = map_id
        if images:
            from pytmx.util_pygame import load_pygame
            self.tmx = load_pygame(map_path(map_id))
        else:
            self.tmx = pytmx.TiledMap(map_path(map_id))
        p = self.tmx.properties
        self.name = p.get("name", map_id)
        self.w, self.h = self.tmx.width, self.tmx.height
        self.start = (p.get("start_x", 1), p.get("start_y", 1))
        self.encounters = _json_prop(p, "encounters", [])
        self.bgm = p.get("bgm") or None
        self.objects = [MapObject(o) for o in self.tmx.objects]
        self._solid = [[False] * self.w for _ in range(self.h)]
        self._encounter = [[False] * self.w for _ in range(self.h)]
        for layer in self.tmx.visible_layers:
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue
            for x, y, gid in layer:
                if not gid:
                    continue
                props = self.tmx.get_tile_properties_by_gid(gid) or {}
                if props.get("solid"):
                    self._solid[y][x] = True
                if props.get("encounter"):
                    self._encounter[y][x] = True
        self.surface = self._render() if images else None

    def _render(self):
        import pygame
        surf = pygame.Surface((self.w * T, self.h * T), pygame.SRCALPHA)
        for layer in self.tmx.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, img in layer.tiles():
                    surf.blit(img, (x * T, y * T))
        return surf

    def inside(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def solid(self, x, y):
        return not self.inside(x, y) or self._solid[y][x]

    def encounter_tile(self, x, y):
        return self.inside(x, y) and self._encounter[y][x]

    def objects_of(self, kind):
        return [o for o in self.objects if o.type == kind]

    def object_at(self, x, y, kinds=None):
        for o in self.objects:
            if (o.x, o.y) == (x, y) and (kinds is None or o.type in kinds):
                return o
        return None


def meta(map_id):
    """Cached logic-only FieldMap (no images) for lookups like encounter groups."""
    if map_id not in _meta_cache:
        _meta_cache[map_id] = FieldMap(map_id)
    return _meta_cache[map_id]


def validate(monsters, items):
    errs = []
    ids = all_map_ids()
    if not ids:
        return ["no maps found in data/maps"]
    for mid in ids:
        m = meta(mid)
        if m.bgm and m.bgm not in config.BGM:
            errs.append(f"map {mid}: unknown bgm {m.bgm}")
        if m.solid(*m.start):
            errs.append(f"map {mid}: start {m.start} is blocked")
        for group in m.encounters:
            errs += [f"map {mid}: unknown monster {x}" for x in group if x not in monsters]
        for o in m.objects:
            if o.type == "warp":
                to = o.props.get("to_map")
                if to not in ids:
                    errs.append(f"map {mid}: warp {o.name} to unknown map {to}")
                elif meta(to).solid(o.props["to_x"], o.props["to_y"]):
                    errs.append(f"map {mid}: warp {o.name} lands on a blocked tile")
            elif o.type == "npc":
                sprite = o.props.get("sprite", 2)
                if not isinstance(sprite, int) or not 0 <= sprite < NPC_SPRITES:
                    errs.append(f"map {mid}: npc {o.name} sprite {sprite} not in 0..{NPC_SPRITES - 1}")
                if o.props.get("facing", "down") not in FACINGS:
                    errs.append(f"map {mid}: npc {o.name} bad facing {o.props.get('facing')}")
                wander = o.props.get("wander", 0)
                if not isinstance(wander, int) or wander < 0:
                    errs.append(f"map {mid}: npc {o.name} bad wander {wander}")
                if m.solid(o.x, o.y):
                    errs.append(f"map {mid}: npc {o.name} stands on a blocked tile")
            elif o.type == "chest" and o.props.get("item") not in items:
                errs.append(f"map {mid}: chest {o.name} has unknown item {o.props.get('item')}")
            elif o.type not in ("npc", "sign", "chest", "warp"):
                errs.append(f"map {mid}: unknown object type {o.type}")
    return errs
