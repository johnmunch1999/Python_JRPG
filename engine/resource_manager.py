"""Loads and caches assets. Works from source and from a PyInstaller bundle."""
import os
import sys

import pygame


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

    def play_music(self, rel: str, loop: bool = True, volume: float = 0.5):
        if not self.sound_enabled:
            return
        try:
            pygame.mixer.music.load(asset_path(rel))
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(-1 if loop else 0)
        except pygame.error:
            pass

    def stop_music(self, fade_ms: int = 300):
        if self.sound_enabled:
            pygame.mixer.music.fadeout(fade_ms)
