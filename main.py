from engine.game_engine import GameEngine
from scenes.title_scene import TitleScene

if __name__ == "__main__":
    engine = GameEngine()
    engine.run(TitleScene(engine))
