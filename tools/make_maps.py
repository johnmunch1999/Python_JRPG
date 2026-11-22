"""Generate data/maps/*.tmx (Tiled format) from the ASCII layouts below.

The output opens in the Tiled editor. Once a map is hand-edited in Tiled,
remove it from MAPS here so it is not overwritten.

Usage:  python tools/make_maps.py
"""
import json
import os
from xml.sax.saxutils import quoteattr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "maps")
TILESET = "town.tsx"

# char -> (ground tile, deco tile or None). Tile ids index kenney_tiny_town tilemap_packed.png.
LEGEND = {
    ".": (0, None), "*": (2, None), "=": (25, None), ":": (43, None), ";": (1, None),
    "T": (0, 28), "B": (0, 5), "F": (0, 81), "S": (0, 83),
    "a": (0, 52), "b": (0, 53), "c": (0, 54),
    "d": (0, 64), "e": (0, 65), "f": (0, 66),
    "g": (0, 84), "h": (0, 85),
}
TILE_PROPS = {
    1: {"encounter": True},
    28: {"solid": True}, 5: {"solid": True}, 81: {"solid": True}, 83: {"solid": True},
    52: {"solid": True}, 53: {"solid": True}, 54: {"solid": True},
    64: {"solid": True}, 65: {"solid": True}, 66: {"solid": True},
    84: {"solid": True}, 85: {"solid": True},
}

MAPS = {
    "village": {
        "name": "시작의 마을",
        "bgm": "village",
        "start": (4, 6),
        "encounters": [],
        "rows": [
            "TTTTTTTTTTTTTTTTTTTTTTTT",
            "T......*.......*.......T",
            "T..abc.......abc...*...T",
            "T..def.......def.......T",
            "T..ghg.......ghg.......T",
            "T...=.........=........T",
            "T...============.......T",
            "T.*....=.....*....BB...T",
            "T......=...............T",
            "T..FFF.=..S....*.......T",
            "T......=...............T",
            "T.*....=.......B.......T",
            "T......=...............T",
            "TTTTTTT=TTTTTTTTTTTTTTTT",
        ],
        "objects": [
            {"type": "npc", "name": "촌장", "x": 5, "y": 7, "props": {
                "sprite": 2, "facing": "down",
                "dialogue": [["어서 오게, 여행자여.", "마을 남쪽 들판에는 몬스터가 나온다네."],
                             ["C 또는 Tab 키로 메뉴를 열 수 있지.", "장비를 챙기고 조심해서 다녀오게!"]]}},
            {"type": "npc", "name": "여관 주인", "x": 15, "y": 5, "props": {
                "sprite": 5, "facing": "down", "action": "inn",
                "dialogue": [["지친 얼굴이구먼.", "푹 쉬었다 가게. 돈은 안 받네."]]}},
            {"type": "npc", "name": "꼬마", "x": 18, "y": 9, "props": {
                "sprite": 4, "facing": "left", "wander": 2,
                "dialogue": [["들판에 갔다가 박쥐한테 쫓겼어!", "박쥐는 엄청 빨라서 도망치기 어려워."]]}},
            {"type": "sign", "name": "표지판", "x": 10, "y": 9, "props": {
                "dialogue": [["↓ 남쪽: 바람의 들판", "(풀숲에서 몬스터가 나타남)"]]}},
            {"type": "chest", "name": "village_chest_1", "x": 20, "y": 3, "props": {"item": "potion", "qty": 2}},
            {"type": "warp", "name": "to_meadow", "x": 7, "y": 13, "props": {
                "to_map": "meadow", "to_x": 7, "to_y": 1, "facing": "down"}},
        ],
    },
    "meadow": {
        "name": "바람의 들판",
        "bgm": "meadow",
        "start": (7, 1),
        "encounters": [["slime"], ["slime", "slime"], ["bat"], ["slime", "bat"], ["goblin"]],
        "rows": [
            "TTTTTTT=TTTTTTTTTTTTTTTT",
            "T......=...............T",
            "T......=..;;;;;;;;;....T",
            "T..;;;;=;;;;;;;;;;;;...T",
            "T..;;;;=;;;;;;;;;;;;...T",
            "T..;;;;===========;;...T",
            "T..;;;;;;;;;;;;;;=;;...T",
            "T......;;;;;;;;;;=.....T",
            "T.BB...;;;;;;;;;;=..B..T",
            "T......;;;;;;;;;;=.....T",
            "T..*...........;;=.....T",
            "T....T.....:::...=.....T",
            "T..........:::.........T",
            "TTTTTTTTTTTTTTTTTTTTTTTT",
        ],
        "objects": [
            {"type": "chest", "name": "meadow_chest_1", "x": 12, "y": 12, "props": {"item": "iron_sword", "qty": 1}},
            {"type": "warp", "name": "to_village", "x": 7, "y": 0, "props": {
                "to_map": "village", "to_x": 7, "to_y": 12, "facing": "up"}},
        ],
    },
}


def prop_xml(props, indent):
    if not props:
        return ""
    pad = " " * indent
    out = [pad + "<properties>"]
    for k, v in props.items():
        if isinstance(v, bool):
            out.append(f'{pad} <property name="{k}" type="bool" value="{str(v).lower()}"/>')
        elif isinstance(v, int):
            out.append(f'{pad} <property name="{k}" type="int" value="{v}"/>')
        elif isinstance(v, str):
            out.append(f'{pad} <property name="{k}" value={quoteattr(v)}/>')
        else:  # lists/dicts are stored as JSON strings
            out.append(f'{pad} <property name="{k}" value={quoteattr(json.dumps(v, ensure_ascii=False))}/>')
    out.append(pad + "</properties>")
    return "\n".join(out) + "\n"


def write_tileset():
    tiles = "".join(f' <tile id="{tid}">\n{prop_xml(p, 2)} </tile>\n' for tid, p in sorted(TILE_PROPS.items()))
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<tileset version="1.10" tiledversion="1.10.2" name="town" tilewidth="16" tileheight="16" '
           'tilecount="132" columns="12">\n'
           ' <image source="../../assets/maps/kenney_tiny_town/Tilemap/tilemap_packed.png" '
           'width="192" height="176"/>\n' + tiles + '</tileset>\n')
    with open(os.path.join(OUT, TILESET), "w", encoding="utf-8") as f:
        f.write(xml)


def write_map(map_id, m):
    rows = m["rows"]
    h, w = len(rows), len(rows[0])
    assert all(len(r) == w for r in rows), f"{map_id}: ragged rows"
    ground, deco = [], []
    for r in rows:
        for c in r:
            g, d = LEGEND[c]
            ground.append(g + 1)
            deco.append(0 if d is None else d + 1)

    def csv(data):
        return "\n" + ",\n".join(",".join(str(v) for v in data[y * w:(y + 1) * w]) for y in range(h)) + "\n"

    objs = []
    for i, o in enumerate(m["objects"], 1):
        objs.append(f'  <object id="{i}" name={quoteattr(o["name"])} type="{o["type"]}" '
                    f'x="{o["x"] * 16}" y="{o["y"] * 16}" width="16" height="16">\n'
                    f'{prop_xml(o["props"], 3)}  </object>')
    map_props = {"name": m["name"], "bgm": m.get("bgm", ""), "start_x": m["start"][0], "start_y": m["start"][1],
                 "encounters": m["encounters"]}
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<map version="1.10" tiledversion="1.10.2" orientation="orthogonal" renderorder="right-down" '
           f'width="{w}" height="{h}" tilewidth="16" tileheight="16" infinite="0" '
           f'nextlayerid="4" nextobjectid="{len(objs) + 1}">\n'
           + prop_xml(map_props, 1) +
           f' <tileset firstgid="1" source="{TILESET}"/>\n'
           f' <layer id="1" name="ground" width="{w}" height="{h}">\n  <data encoding="csv">{csv(ground)}</data>\n </layer>\n'
           f' <layer id="2" name="deco" width="{w}" height="{h}">\n  <data encoding="csv">{csv(deco)}</data>\n </layer>\n'
           ' <objectgroup id="3" name="objects">\n' + "\n".join(objs) + '\n </objectgroup>\n'
           '</map>\n')
    with open(os.path.join(OUT, map_id + ".tmx"), "w", encoding="utf-8") as f:
        f.write(xml)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    write_tileset()
    for map_id, m in MAPS.items():
        write_map(map_id, m)
        print("wrote", map_id)
