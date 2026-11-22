"""Party member: static definition from characters.json + mutable progress."""
from systems import data_loader

STATS = ("hp", "mp", "atk", "def", "agi")


def exp_to_next(level):
    return 10 * level * level


class Character:
    def __init__(self, char_id, level=1, exp=0, hp=None, mp=None, weapon=None, armor=None):
        self.id = char_id
        self.data = data_loader.characters()[char_id]
        self.name = self.data["name"]
        self.level, self.exp = level, exp
        self.weapon, self.armor = weapon, armor
        self.hp = self.max_hp if hp is None else min(hp, self.max_hp)
        self.mp = self.max_mp if mp is None else min(mp, self.max_mp)

    def base_stat(self, key):
        return self.data["base"][key] + self.data["growth"].get(key, 0) * (self.level - 1)

    def stat(self, key):
        """Base stat plus equipment bonuses."""
        value = self.base_stat(key)
        for item_id in (self.weapon, self.armor):
            if item_id:
                value += data_loader.items()[item_id].get("stats", {}).get(key, 0)
        return value

    @property
    def max_hp(self): return self.stat("hp")

    @property
    def max_mp(self): return self.stat("mp")

    @property
    def alive(self): return self.hp > 0

    @property
    def skills(self): return list(self.data.get("skills", []))

    def gain_exp(self, amount):
        """Adds exp; returns number of levels gained. Level up refills HP/MP."""
        self.exp += amount
        gained = 0
        while self.exp >= exp_to_next(self.level):
            self.exp -= exp_to_next(self.level)
            self.level += 1
            gained += 1
        if gained:
            self.hp, self.mp = self.max_hp, self.max_mp
        return gained

    def to_row(self):
        return dict(char_id=self.id, level=self.level, exp=self.exp, hp=self.hp, mp=self.mp,
                    weapon=self.weapon, armor=self.armor)

    @classmethod
    def from_row(cls, row):
        return cls(row["char_id"], row["level"], row["exp"], row["hp"], row["mp"],
                   row["weapon"], row["armor"])
