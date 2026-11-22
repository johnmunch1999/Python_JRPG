"""A monster instance in battle, built from monsters.json."""
from systems import data_loader


class Enemy:
    def __init__(self, monster_id, suffix=""):
        self.id = monster_id
        self.data = data_loader.monsters()[monster_id]
        self.name = self.data["name"] + suffix
        self.max_hp = self.hp = self.data["hp"]
        self.max_mp = self.mp = 0

    def stat(self, key):
        return self.data[key]

    @property
    def alive(self):
        return self.hp > 0
