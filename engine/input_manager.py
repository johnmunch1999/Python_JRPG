"""Maps raw keys to abstract actions (confirm/cancel/menu/directions)."""
import pygame

KEYMAP = {
    "confirm": (pygame.K_z, pygame.K_RETURN, pygame.K_SPACE),
    "cancel": (pygame.K_x, pygame.K_ESCAPE, pygame.K_BACKSPACE),
    "menu": (pygame.K_c, pygame.K_TAB),
    "up": (pygame.K_UP, pygame.K_w),
    "down": (pygame.K_DOWN, pygame.K_s),
    "left": (pygame.K_LEFT, pygame.K_a),
    "right": (pygame.K_RIGHT, pygame.K_d),
}
_KEY_TO_ACTION = {k: a for a, keys in KEYMAP.items() for k in keys}
DIRECTIONS = ("up", "down", "left", "right")


class InputManager:
    def __init__(self):
        self.pressed = set()      # actions newly pressed this frame
        self._held_keys = set()   # raw keys currently down
        self._dir_order = []      # held directions, most recent last

    def begin_frame(self):
        self.pressed.clear()

    def handle_event(self, event):
        action = _KEY_TO_ACTION.get(getattr(event, "key", None))
        if not action:
            return
        if event.type == pygame.KEYDOWN:
            self.pressed.add(action)
            self._held_keys.add(event.key)
            if action in DIRECTIONS:
                if action in self._dir_order:
                    self._dir_order.remove(action)
                self._dir_order.append(action)
        elif event.type == pygame.KEYUP:
            self._held_keys.discard(event.key)
            if action in self._dir_order and not self.is_held(action):
                self._dir_order.remove(action)

    def was_pressed(self, action: str) -> bool:
        return action in self.pressed

    def is_held(self, action: str) -> bool:
        return any(k in self._held_keys for k in KEYMAP[action])

    def direction(self):
        """Most recently pressed direction still held, or None."""
        return self._dir_order[-1] if self._dir_order else None
