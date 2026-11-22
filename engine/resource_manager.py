"""Loads and caches assets. Works from source and from a PyInstaller bundle."""
import os
import random
import sys

import pygame

import config


def base_path() -> str:
    if hasattr(sys, "_MEIPASS"):  # PyInstaller one-file temp dir
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def asset_path(*parts: str) -> str:
    return os.path.join(base_path(), "assets", *parts)


class ResourceManager:
    def __init__(self):
        self._images = {}
        self._fonts = {}
        self._sounds = {}
        self.sound_enabled = pygame.mixer.get_init() is not None
        self.current_music = None
        self._jingle_channel = None
        if self.sound_enabled:
            pygame.mixer.set_reserved(1)
            self._jingle_channel = pygame.mixer.Channel(0)

    def image(self, rel: str) -> pygame.Surface:
        if rel not in self._images:
            self._images[rel] = pygame.image.load(asset_path(rel)).convert_alpha()
        return self._images[rel]

    def font(self, rel: str, size: int) -> pygame.font.Font:
        key = (rel, size)
        if key not in self._fonts:
            try:
                self._fonts[key] = pygame.font.Font(asset_path(rel), size)
            except (FileNotFoundError, OSError):
                self._fonts[key] = pygame.font.Font(None, size)
        return self._fonts[key]

    def sound(self, rel: str):
        if not self.sound_enabled:
            return None
        if rel not in self._sounds:
            try:
                self._sounds[rel] = pygame.mixer.Sound(asset_path(rel))
            except (FileNotFoundError, pygame.error):
                self._sounds[rel] = None
        return self._sounds[rel]

    def play(self, rel: str, volume: float = 0.6):
        snd = self.sound(rel)
        if snd:
            snd.set_volume(volume)
            snd.play()

    def sfx(self, name: str, volume: float = 1.0):
        """Play a named effect from config.SFX."""
        rel = config.SFX.get(name)
        if isinstance(rel, list):
            rel = random.choice(rel)
        if rel:
            self.play(rel, volume * config.SFX_VOLUME)

    def music(self, name: str | None, fade_ms: int = 400):
        """Switch BGM by name (config.BGM). Same track keeps playing; None stops."""
        if name == self.current_music:
            return
        self.current_music = name
        if not self.sound_enabled:
            return
        if name is None:
            pygame.mixer.music.fadeout(fade_ms)
            return
        if self._jingle_channel:
            self._jingle_channel.fadeout(200)
        try:
            pygame.mixer.music.load(asset_path(config.BGM[name]))
            pygame.mixer.music.set_volume(config.MUSIC_VOLUME)
            pygame.mixer.music.play(-1, fade_ms=fade_ms)
        except (pygame.error, KeyError):
            pass

    def jingle(self, name: str):
        """Stop the BGM and play a short fanfare on its own channel."""
        self.music(None, 150)
        snd = self.sound(config.JINGLES[name])
        if snd and self._jingle_channel:
            snd.set_volume(config.MUSIC_VOLUME)
            self._jingle_channel.play(snd)

    def jingle_playing(self) -> bool:
        return bool(self._jingle_channel and self._jingle_channel.get_busy())

    def stop_music(self, fade_ms: int = 300):
        self.music(None, fade_ms)
