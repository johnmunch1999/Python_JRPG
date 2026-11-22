import math

import pygame

import config
from engine.scene import Scene
from gui.menu_list import MenuList
from gui.window import draw_text

BG = "backgrounds/fantasy_background/fantasy_back_0.png"


class TitleScene(Scene):
    def on_enter(self):
        self.engine.state = None   # leaving a game (unsaved progress is dropped)
        self.menu = MenuList(self.res, ["새 게임", ("이어하기", self.engine.saves.has_any()), "종료"],
                             (110, 150, 100, 58), cancellable=False)
        self.title_font = self.res.font(config.FONT_BOLD, 24)
        self.small = self.res.font(config.FONT_SMALL, config.FONT_SIZE_SMALL)
        self.t = 0.0
        self.res.music("title")
        self.notice = None
        if self.engine.saves and self.engine.save_warning:
            from gui.dialogue_box import DialogueBox
            self.notice = DialogueBox(self.res, [self.engine.save_warning])
            self.engine.save_warning = None
        try:
            bg = self.res.image(BG)
            self.bg = pygame.transform.scale(bg, (config.VIRTUAL_W, config.VIRTUAL_H))
        except FileNotFoundError:
            self.bg = None

    def on_resume(self):
        self.menu.items[1] = ("이어하기", self.engine.saves.has_any())

    def update(self, dt):
        self.t += dt
        if self.notice:
            if self.notice.update(self.input, dt):
                self.notice = None
            return
        choice = self.menu.update(self.input, dt)
        if choice == 0:
            from engine.state_manager import GameState
            from scenes.world_scene import WorldScene
            self.engine.state = GameState.new_game()
            self.engine.scenes.change(WorldScene(self.engine))
        elif choice == 1:
            from scenes.save_slot_scene import SaveSlotScene
            self.engine.scenes.push(SaveSlotScene(self.engine, "load"))
        elif choice == 2:
            self.engine.quit()

    def draw(self, surface):
        if self.bg:
            surface.blit(self.bg, (0, 0))
        y = 50 + int(math.sin(self.t * 2) * 3)
        draw_text(surface, self.title_font, "Classic JRPG", (config.VIRTUAL_W // 2, y),
                  config.COLOR_HIGHLIGHT, align="center")
        draw_text(surface, self.small, "Project", (config.VIRTUAL_W // 2, y + 30), align="center")
        self.menu.draw(surface, active=self.notice is None)
        draw_text(surface, self.small, "Z/Enter: 확인   X/Esc: 취소",
                  (config.VIRTUAL_W // 2, 224), config.COLOR_TEXT_DIM, align="center")
        if self.notice:
            self.notice.draw(surface)
