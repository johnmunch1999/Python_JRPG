"""The single mutable game state shared by all scenes (what gets saved)."""
import copy

from entities.character import Character
from systems import data_loader


class GameState:
    def __init__(self):
        self.party = []
        self.gold = 0
        self.inventory = {}          # item_id -> qty
        self.map = "village"
        self.x, self.y, self.facing = 0, 0, "down"
        self.playtime = 0.0
        self.flags = set()           # one-shot world events, e.g. "chest:meadow_chest_1"
        self.slot = None             # slot this game was loaded from / last saved to

    @classmethod
    def new_game(cls):
        ng = copy.deepcopy(data_loader.new_game())
        s = cls()
        eq = ng.get("equipment", {})
        s.party = [Character(cid, weapon=eq.get(cid, {}).get("weapon"),
                             armor=eq.get(cid, {}).get("armor")) for cid in ng["party"]]
        s.gold = ng["gold"]
        s.inventory = dict(ng["inventory"])
        loc = ng["location"]
        s.map, s.x, s.y, s.facing = loc["map"], loc["x"], loc["y"], loc["facing"]
        return s

    @property
    def leader(self):
        return self.party[0]

    def encounter_groups(self):
        """List of monster-id groups that can appear on the current map."""
        from systems import field_map
        return field_map.meta(self.map).encounters

    def equip(self, char, slot, item_id):
        """Equip item_id (or None to unequip) in slot 'weapon'/'armor'.
        The new item leaves the bag, the old one goes back into it."""
        if item_id and not self.remove_item(item_id):
            return False
        old = getattr(char, slot)
        if old:
            self.add_item(old)
        setattr(char, slot, item_id)
        char.hp, char.mp = min(char.hp, char.max_hp), min(char.mp, char.max_mp)
        return True

    def add_item(self, item_id, qty=1):
        self.inventory[item_id] = self.inventory.get(item_id, 0) + qty

    def remove_item(self, item_id, qty=1):
        have = self.inventory.get(item_id, 0)
        if have < qty:
            return False
        if have == qty:
            del self.inventory[item_id]
        else:
            self.inventory[item_id] = have - qty
        return True
