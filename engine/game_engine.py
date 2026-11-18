"""Pygame init + main loop. Renders to a low-res surface and scales it up."""
import os

import pygame

import config
from engine.input_manager import InputManager
from engine.resource_manager import ResourceManager
from engine.scene_manager import SceneManager


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
        self.running = False
        # Automated smoke tests: quit after N frames (0 = unlimited).
        self.max_frames = int(os.environ.get("JRPG_MAX_FRAMES", "0"))
        self.frame = 0

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
        pygame.quit()
