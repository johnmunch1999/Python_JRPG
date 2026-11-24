"""Global settings for the game."""
TITLE = "Classic JRPG Project"
VIRTUAL_W, VIRTUAL_H = 320, 240   # internal pixel-art resolution
SCALE = 3                         # window = 960x720
FPS = 60
TILE = 16

# Classic blue window palette
COLOR_BG = (12, 12, 24)
COLOR_WINDOW_TOP = (40, 56, 160)
COLOR_WINDOW_BOTTOM = (12, 16, 72)
COLOR_BORDER = (232, 232, 240)
COLOR_TEXT = (248, 248, 248)
COLOR_TEXT_DIM = (140, 140, 160)
COLOR_HIGHLIGHT = (255, 224, 96)

FONT_MAIN = "fonts/galmuri/Galmuri11.ttf"
FONT_BOLD = "fonts/galmuri/Galmuri11-Bold.ttf"
FONT_SMALL = "fonts/galmuri/Galmuri9.ttf"
FONT_SIZE = 12
FONT_SIZE_SMALL = 10

# --- Paths (work both from source and from a PyInstaller bundle) ---
import os as _os
import sys as _sys

BASE_DIR = getattr(_sys, "_MEIPASS", _os.path.dirname(_os.path.abspath(__file__)))
DATA_DIR = _os.path.join(BASE_DIR, "data")
# Dev: ./saves/game.db. Frozen exe: saves/ next to the .exe (the bundle dir is a
# temp folder wiped on exit). Override with JRPG_SAVE_DB (tests, custom location).
_APP_DIR = (_os.path.dirname(_os.path.abspath(_sys.executable)) if getattr(_sys, "frozen", False)
            else _os.path.dirname(_os.path.abspath(__file__)))
SAVE_DB = _os.environ.get("JRPG_SAVE_DB") or _os.path.join(_APP_DIR, "saves", "game.db")
SAVE_SLOTS = 3

# --- Audio ---------------------------------------------------------
MUSIC_VOLUME = 0.5
SFX_VOLUME = 0.7
_K = "sounds/kenney_rpg_audio/OGG/"
# One name per game event; a list means "pick a variant each time".
SFX = {
    "cursor": _K + "cloth1.ogg", "ok": _K + "metalClick.ogg", "cancel": _K + "bookClose.ogg",
    "buzzer": _K + "cloth2.ogg", "text": _K + "bookFlip1.ogg",
    "step": [_K + f"footstep0{i}.ogg" for i in range(10)],
    "chest": _K + "doorOpen_1.ogg", "warp": _K + "creak1.ogg", "equip": _K + "metalLatch.ogg",
    "heal": _K + "bookOpen.ogg", "coins": _K + "handleCoins.ogg", "save": _K + "bookPlace1.ogg",
    "hit": [_K + "knifeSlice.ogg", _K + "knifeSlice2.ogg"], "crit": _K + "chop.ogg",
    "swing": [_K + f"drawKnife{i}.ogg" for i in (1, 2, 3)], "enemy_hit": _K + "metalPot1.ogg",
    "defeat_enemy": _K + "dropLeather.ogg", "magic": _K + "beltHandle1.ogg",
}
_G = "bgm/generated/"
BGM = {
    "title": _G + "title.wav", "village": _G + "village.wav", "meadow": _G + "meadow.wav",
    "battle": "bgm/hydrogene_battle1/jrpg_battle_loop.mp3",
}
JINGLES = {"victory": _G + "victory.wav", "levelup": _G + "levelup.wav", "gameover": _G + "gameover.wav"}
