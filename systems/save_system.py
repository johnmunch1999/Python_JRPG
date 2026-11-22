"""SQLite save slots.

Schema version lives in PRAGMA user_version; MIGRATIONS[i] upgrades i -> i+1.
Each save fully replaces one slot inside a single transaction, so a crash never
leaves a half-written slot. RNG state is intentionally not saved (see docs/save_format.md).
"""
import datetime
import os
import sqlite3

import config
from engine.state_manager import GameState
from entities.character import Character

DATA_VERSION = 1   # version of the saved *content* format, stored per slot

MIGRATIONS = [
    # 0 -> 1: initial schema
    """
    CREATE TABLE save_slots (
        slot         INTEGER PRIMARY KEY CHECK (slot >= 1),
        data_version INTEGER NOT NULL,
        saved_at     TEXT    NOT NULL,
        playtime     REAL    NOT NULL DEFAULT 0,
        map          TEXT    NOT NULL,
        x            INTEGER NOT NULL,
        y            INTEGER NOT NULL,
        facing       TEXT    NOT NULL,
        gold         INTEGER NOT NULL CHECK (gold >= 0)
    );
    CREATE TABLE party_members (
        slot     INTEGER NOT NULL REFERENCES save_slots(slot) ON DELETE CASCADE,
        position INTEGER NOT NULL,
        char_id  TEXT    NOT NULL,
        level    INTEGER NOT NULL,
        exp      INTEGER NOT NULL,
        hp       INTEGER NOT NULL,
        mp       INTEGER NOT NULL,
        weapon   TEXT,
        armor    TEXT,
        PRIMARY KEY (slot, position)
    );
    CREATE TABLE inventory (
        slot    INTEGER NOT NULL REFERENCES save_slots(slot) ON DELETE CASCADE,
        item_id TEXT    NOT NULL,
        qty     INTEGER NOT NULL CHECK (qty > 0),
        PRIMARY KEY (slot, item_id)
    );
    """,
    # 1 -> 2: one-shot world flags (opened chests, story events)
    """
    CREATE TABLE flags (
        slot INTEGER NOT NULL REFERENCES save_slots(slot) ON DELETE CASCADE,
        flag TEXT    NOT NULL,
        PRIMARY KEY (slot, flag)
    );
    """,
]
SCHEMA_VERSION = len(MIGRATIONS)


class SaveSystem:
    @staticmethod
    def default_path():
        return config.SAVE_DB

    def __init__(self, path=None):
        self.path = path or config.SAVE_DB
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        try:
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")
            self._migrate()
        except Exception:
            self.conn.close()   # release the file so the caller can move it aside
            raise

    def _migrate(self):
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise RuntimeError(f"Save DB schema v{version} is newer than this game (v{SCHEMA_VERSION})")
        for v in range(version, SCHEMA_VERSION):
            with self.conn:
                self.conn.executescript("BEGIN;" + MIGRATIONS[v] + f"PRAGMA user_version = {v + 1};COMMIT;")

    def close(self):
        self.conn.close()

    # --- queries ----------------------------------------------------
    def list_slots(self):
        """{slot: summary dict} for occupied slots."""
        rows = self.conn.execute("""
            SELECT s.slot, s.saved_at, s.playtime, s.map, p.char_id, p.level
            FROM save_slots s LEFT JOIN party_members p ON p.slot = s.slot AND p.position = 0
        """).fetchall()
        return {r["slot"]: dict(r) for r in rows}

    def has_any(self):
        return self.conn.execute("SELECT 1 FROM save_slots LIMIT 1").fetchone() is not None

    # --- write ------------------------------------------------------
    def save(self, slot, state):
        now = datetime.datetime.now().isoformat(timespec="seconds")
        with self.conn:  # one transaction
            self.conn.execute("DELETE FROM save_slots WHERE slot = ?", (slot,))  # cascades
            self.conn.execute(
                "INSERT INTO save_slots VALUES (?,?,?,?,?,?,?,?,?)",
                (slot, DATA_VERSION, now, state.playtime, state.map, state.x, state.y,
                 state.facing, state.gold))
            self.conn.executemany(
                "INSERT INTO party_members VALUES (:slot,:position,:char_id,:level,:exp,:hp,:mp,:weapon,:armor)",
                [dict(c.to_row(), slot=slot, position=i) for i, c in enumerate(state.party)])
            self.conn.executemany(
                "INSERT INTO inventory VALUES (?,?,?)",
                [(slot, i, q) for i, q in state.inventory.items() if q > 0])
            self.conn.executemany("INSERT INTO flags VALUES (?,?)", [(slot, f) for f in sorted(state.flags)])
        state.slot = slot

    def delete(self, slot):
        with self.conn:
            self.conn.execute("DELETE FROM save_slots WHERE slot = ?", (slot,))

    # --- read -------------------------------------------------------
    def load(self, slot):
        row = self.conn.execute("SELECT * FROM save_slots WHERE slot = ?", (slot,)).fetchone()
        if row is None:
            return None
        if row["data_version"] > DATA_VERSION:
            raise RuntimeError(f"Slot {slot} was saved by a newer game version")
        s = GameState()
        s.slot = slot
        s.playtime, s.map, s.x, s.y, s.facing, s.gold = (
            row["playtime"], row["map"], row["x"], row["y"], row["facing"], row["gold"])
        s.party = [Character.from_row(r) for r in self.conn.execute(
            "SELECT * FROM party_members WHERE slot = ? ORDER BY position", (slot,))]
        s.inventory = {r["item_id"]: r["qty"] for r in self.conn.execute(
            "SELECT item_id, qty FROM inventory WHERE slot = ?", (slot,))}
        s.flags = {r["flag"] for r in self.conn.execute("SELECT flag FROM flags WHERE slot = ?", (slot,))}
        return s
