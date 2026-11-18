"""Placeholder battle screen. Real turn rules arrive in stage 3."""
import math
import random

import pygame

import config
from engine.scene import Scene
from gui.dialogue_box import DialogueBox
from gui.menu_list import MenuList
from gui.window import draw_text, draw_window

BG = "backgrounds/nidhoggn_battlebacks/battleback{}.png"
MONSTER = "monsters/isaiah658_50_monsters/Monsters/Normal Colors/Monster #{} Front Normal Color Palette.png"
BGM = "bgm/hydrogene_battle1/jrpg_battle_loop.mp3"
SND_HIT = "sounds/kenney_rpg_audio/OGG/knifeSlice.ogg"


class BattleScene(Scene):
    def on_enter(self):
        bg = self.res.image(BG.format(random.randint(1, 10)))
        self.bg = pygame.transform.scale(bg, (config.VIRTUAL_W, 148))
        self.monster_img = None
        for _ in range(5):  # pack numbering has gaps; try a few
            try:
                img = self.res.image(MONSTER.format(random.randint(1, 50)))
                self.monster_img = pygame.transform.scale(img, (96, 96))
                break
            except FileNotFoundError:
                continue
        self.monster_hp = self.monster_max = 3
        self.hero_hp, self.hero_max = 30, 30
        self.commands = MenuList(self.res, ["공격", "방어", ("스킬", False), ("아이템", False), "도망"],
                                 (4, 150, 80, 88), cancellable=False)
        self.font = self.res.font(config.FONT_MAIN, config.FONT_SIZE)
        self.message = DialogueBox(self.res, ["몬스터가 나타났다!"], rect=(88, 150, 228, 88))
        self.after_message = None
        self.shake = 0.0
        self.t = 0.0
        self.res.play_music(BGM)

    def on_exit(self):
        self.res.stop_music()

    def _say(self, text, then=None):
        self.message = DialogueBox(self.res, [text], rect=(88, 150, 228, 88))
        self.after_message = then

    def update(self, dt):
        self.t += dt
        self.shake = max(0.0, self.shake - dt)
        if self.message:
            if self.message.update(self.input, dt):
                self.message = None
                if self.after_message:
                    self.after_message()
            return
        choice = self.commands.update(self.input, dt)
        if choice == 0:
            self.monster_hp -= 1
            self.shake = 0.3
            self.res.play(SND_HIT)
            if self.monster_hp <= 0:
                self._say("몬스터를 쓰러뜨렸다!", self._leave)
            else:
                self._say("용사의 공격! 몬스터에게 1 피해.", self._enemy_turn)
        elif choice == 1:
            self._say("용사는 몸을 웅크렸다.", lambda: self._enemy_turn(defending=True))
        elif choice == 4:
            self._say("무사히 도망쳤다!", self._leave)

    def _enemy_turn(self, defending=False):
        dmg = 2 if defending else 5
        self.hero_hp = max(1, self.hero_hp - dmg)
        self._say(f"몬스터의 공격! 용사는 {dmg} 피해를 입었다.")

    def _leave(self):
        self.engine.scenes.pop(fade=True)

    def draw(self, surface):
        surface.blit(self.bg, (0, 0))
        if self.monster_img and self.monster_hp > 0:
            ox = int(math.sin(self.shake * 60) * 3) if self.shake else 0
            oy = int(math.sin(self.t * 2) * 2)
            surface.blit(self.monster_img, (112 + ox, 40 + oy))
        draw_window(surface, (230, 4, 86, 34))
        draw_text(surface, self.font, "용사", (238, 8))
        draw_text(surface, self.font, f"HP {self.hero_hp}/{self.hero_max}", (238, 21))
        self.commands.draw(surface, active=self.message is None)
        if self.message:
            self.message.draw(surface)
        else:
            draw_window(surface, (88, 150, 228, 88))
            draw_text(surface, self.font, "명령을 선택하세요.", (96, 156), config.COLOR_TEXT_DIM)
