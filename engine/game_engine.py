"""Pygame init + main loop. Renders to a low-res surface and scales it up."""
import os

import pygame

import config
from engine.input_manager import InputManager
from engine.resource_manager import ResourceManager
from engine.scene_manager import SceneManager
from systems import data_loader
from systems.save_system import SaveSystem


class GameEngine:
    def __init__(self):
        pygame.init()
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except pygame.error:
                pass  # no audio device: run silently
        pygame.display.set_caption(config.TITLE)
        self.window = pygame.display.set_mode(
            (config.VIRTUAL_W * config.SCALE, config.VIRTUAL_H * config.SCALE))
        self.screen = pygame.Surface((config.VIRTUAL_W, config.VIRTUAL_H))
        self.clock = pygame.time.Clock()
        self.input = InputManager()
        self.resources = ResourceManager()
        self.scenes = SceneManager(self)
        data_loader.load_all()        # fail fast on broken JSON
        self.state = None             # GameState of the running game (None on title)
        self._saves = None
        self.save_warning = None      # shown once on the title screen if the save file had problems
        self.running = False
        # Automated smoke tests: quit after N frames (0 = unlimited).
        self.max_frames = int(os.environ.get("JRPG_MAX_FRAMES", "0"))
        self.frame = 0

    @property
    def saves(self):
        if self._saves is None:
            self._saves = self._open_saves()
        return self._saves

    def _open_saves(self):
        """Open the save DB; never let a bad file stop the game from starting."""
        import datetime
        import sqlite3
        try:
            return SaveSystem()
        except RuntimeError:
            # written by a newer version of the game: leave it untouched, play without saving to it
            self.save_warning = ["세이브 파일이 더 새로운 버전의 게임에서 만들어졌습니다.",
                                 "이번 실행에서는 저장하지 않습니다."]
            return SaveSystem(":memory:")
        except sqlite3.DatabaseError:
            path = SaveSystem.default_path()
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = f"{path}.broken-{stamp}"
            try:
                os.replace(path, backup)
            except OSError:
                self.save_warning = ["세이브 파일을 읽을 수 없습니다.", "이번 실행에서는 저장하지 않습니다."]
                return SaveSystem(":memory:")
            self.save_warning = ["세이브 파일이 손상되어 새로 만들었습니다.",
                                 "기존 파일: " + os.path.basename(backup)]
            return SaveSystem()

    def quit(self):
        self.running = False

    def step(self, dt, events=()):
        """One frame of logic + rendering. Separated out for testing."""
        self.input.begin_frame()
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            self.input.handle_event(event)
        self.scenes.update(dt)
        if self.state:
            self.state.playtime += dt
        self.screen.fill(config.COLOR_BG)
        self.scenes.draw(self.screen)
        pygame.transform.scale(self.screen, self.window.get_size(), self.window)

    def run(self, first_scene):
        self.scenes.change(first_scene, fade=False)
        self.running = True
        while self.running and self.scenes.stack:
            dt = min(self.clock.tick(config.FPS) / 1000.0, 0.1)
            self.step(dt, pygame.event.get())
            pygame.display.flip()
            self.frame += 1
            if self.max_frames and self.frame >= self.max_frames:
                break
        if self._saves:
            self._saves.close()
        pygame.quit()
