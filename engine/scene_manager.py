"""Stack-based scene manager with fade transitions."""
import pygame


class SceneManager:
    FADE_TIME = 0.25

    def __init__(self, engine):
        self.engine = engine
        self.stack = []
        self._pending = None      # (op, scene) applied when fully black
        self._fade = 0.0          # 0 = clear, 1 = black
        self._fade_dir = 0        # +1 fading out, -1 fading in

    @property
    def top(self):
        return self.stack[-1] if self.stack else None

    @property
    def busy(self):
        return self._fade_dir != 0

    # --- public API -------------------------------------------------
    def change(self, scene, fade=True):
        """Replace the whole stack with `scene`."""
        self._request("change", scene, fade)

    def push(self, scene, fade=False):
        """Put `scene` on top (e.g. menu over field, battle over field)."""
        self._request("push", scene, fade)

    def pop(self, fade=False):
        """Close the top scene and resume the one below."""
        self._request("pop", None, fade)

    # --- internals --------------------------------------------------
    def _request(self, op, scene, fade):
        if self.busy:
            return
        if fade:
            self._pending = (op, scene)
            self._fade_dir = 1
        else:
            self._apply(op, scene)

    def _apply(self, op, scene):
        if op == "change":
            while self.stack:
                self.stack.pop().on_exit()
            self.stack.append(scene)
            scene.on_enter()
        elif op == "push":
            if self.top:
                self.top.on_pause()
            self.stack.append(scene)
            scene.on_enter()
        elif op == "pop" and self.stack:
            self.stack.pop().on_exit()
            if self.top:
                self.top.on_resume()

    def update(self, dt):
        if self._fade_dir:
            self._fade += self._fade_dir * dt / self.FADE_TIME
            if self._fade_dir > 0 and self._fade >= 1:
                self._fade = 1
                self._apply(*self._pending)
                self._pending = None
                self._fade_dir = -1
            elif self._fade_dir < 0 and self._fade <= 0:
                self._fade = 0
                self._fade_dir = 0
            return  # scene logic is frozen while fading
        if self.top:
            self.top.update(dt)

    def draw(self, surface):
        start = len(self.stack) - 1
        while start > 0 and self.stack[start].transparent:
            start -= 1
        for scene in self.stack[max(start, 0):]:
            scene.draw(surface)
        if self._fade > 0:
            veil = pygame.Surface(surface.get_size())
            veil.set_alpha(int(255 * self._fade))
            surface.blit(veil, (0, 0))
