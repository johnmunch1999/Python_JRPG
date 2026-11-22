"""Shown after a party wipe. Any confirm returns to the title."""
import config
from engine.scene import Scene
from gui.window import draw_text


class GameOverScene(Scene):
    def on_enter(self):
        self.big = self.res.font(config.FONT_BOLD, 24)
        self.small = self.res.font(config.FONT_SMALL, config.FONT_SIZE_SMALL)
        self.t = 0.0
        self.engine.state = None
        self.res.jingle("gameover")

    def update(self, dt):
        self.t += dt
        if self.t > 1.0 and (self.input.was_pressed("confirm") or self.input.was_pressed("cancel")):
            from scenes.title_scene import TitleScene
            self.engine.scenes.change(TitleScene(self.engine))

    def draw(self, surface):
        cx = config.VIRTUAL_W // 2
        draw_text(surface, self.big, "GAME OVER", (cx, 96), (200, 48, 48), align="center")
        if self.t > 1.0:
            draw_text(surface, self.small, "Z 키를 눌러 타이틀로", (cx, 140), config.COLOR_TEXT_DIM,
                      align="center")
