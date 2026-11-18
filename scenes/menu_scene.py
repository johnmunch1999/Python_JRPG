"""Field menu overlay, drawn on top of the world scene."""
import config
from engine.scene import Scene
from gui.menu_list import MenuList
from gui.window import draw_text, draw_window


class MenuScene(Scene):
    transparent = True

    def on_enter(self):
        self.menu = MenuList(self.res, [("아이템", False), ("장비", False), ("상태", False),
                                        ("저장", False), "타이틀로", "닫기"],
                             (228, 4, 88, 106))
        self.font = self.res.font(config.FONT_MAIN, config.FONT_SIZE)
        self.small = self.res.font(config.FONT_SMALL, config.FONT_SIZE_SMALL)

    def update(self, dt):
        if self.input.was_pressed("menu"):
            self.engine.scenes.pop()
            return
        choice = self.menu.update(self.input, dt)
        if choice in (-1, 5):
            self.engine.scenes.pop()
        elif choice == 4:
            from scenes.title_scene import TitleScene
            self.engine.scenes.change(TitleScene(self.engine))

    def draw(self, surface):
        draw_window(surface, (4, 4, 220, 50))
        draw_text(surface, self.font, "용사   Lv 1", (12, 9))
        draw_text(surface, self.font, "HP 30/30   MP 10/10", (12, 25))
        draw_text(surface, self.small, "회색 항목은 이후 단계에서 구현", (12, 40), config.COLOR_TEXT_DIM)
        self.menu.draw(surface)
