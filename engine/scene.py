"""Base class for every scene."""


class Scene:
    # When True, the scene below on the stack is drawn first (overlay menus).
    transparent = False

    def __init__(self, engine):
        self.engine = engine
        self.res = engine.resources
        self.input = engine.input

    def on_enter(self):
        pass

    def on_exit(self):
        pass

    def on_pause(self):
        pass

    def on_resume(self):
        pass

    def update(self, dt: float):
        pass

    def draw(self, surface):
        pass
