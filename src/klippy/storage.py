from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from .domain import Macro, Printer


def data_directory() -> Path:
    path = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share")) / "KlippyAssistant"
    path.mkdir(parents=True, exist_ok=True)
    return path


class Store:
    """Only settings/operational event codes are persisted. No utterance API exists."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS printers(id TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS macros(printer TEXT, name TEXT, value TEXT NOT NULL,
              PRIMARY KEY(printer,name));
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
              printer TEXT, code TEXT);
        """)
        self.db.commit()

    def close(self):
        self.db.close()

    def get(self, key, default=None):
        row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key, value):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, json.dumps(value)))

    def printers(self):
        return [Printer.model_validate_json(r[0]) for r in self.db.execute("SELECT value FROM printers")]

    def save_printer(self, printer: Printer):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO printers VALUES (?,?)", (printer.id, printer.model_dump_json()))

    def remove_printer(self, printer_id):
        with self.db:
            self.db.execute("DELETE FROM macros WHERE printer=?", (printer_id,))
            self.db.execute("DELETE FROM printers WHERE id=?", (printer_id,))
            if self.get("selected") == printer_id:
                self.db.execute("DELETE FROM settings WHERE key='selected'")

    def macros(self, printer_id):
        return {m.name: m for (value,) in self.db.execute(
            "SELECT value FROM macros WHERE printer=?", (printer_id,)
        ) for m in [Macro.model_validate_json(value)]}

    def replace_macros(self, printer_id, macros):
        with self.db:
            self.db.execute("DELETE FROM macros WHERE printer=?", (printer_id,))
            self.db.executemany("INSERT INTO macros VALUES (?,?,?)", [
                (printer_id, m.name, m.model_dump_json()) for m in macros.values()
            ])

    def event(self, printer_id, code):
        allowed = {"disconnected", "connected", "fault", "paused", "command_sent", "outcome_unknown"}
        if code not in allowed:
            raise ValueError("Operational codes only")
        with self.db:
            self.db.execute("INSERT INTO events(printer,code) VALUES (?,?)", (printer_id, code))
            self.db.execute("DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT 1000)")

    def export(self, path: Path):
        # Macros/addresses are private user configuration. Never export credentials.
        payload = {"version": 1, "printers": [p.model_dump(mode="json") for p in self.printers()],
                   "selected": self.get("selected"), "listening": self.get("listening", {}),
                   "macros": {p.id: [m.model_dump(mode="json") for m in self.macros(p.id).values()]
                              for p in self.printers()}}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def restore(self, path: Path):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") != 1:
            raise ValueError("Unsupported backup")
        printers = [Printer.model_validate_json(json.dumps(p)) for p in payload["printers"]]
        registries = {p.id: [Macro.model_validate_json(json.dumps(m)) for m in
                            payload.get("macros", {}).get(p.id, [])] for p in printers}
        # Restored devices and macros require approval on this installation.
        with self.db:
            self.db.execute("DELETE FROM printers")
            self.db.execute("DELETE FROM macros")
            for p in printers:
                self.db.execute("INSERT INTO printers VALUES (?,?)", (p.id, p.model_copy(
                    update={"approved": False}).model_dump_json()))
                for m in registries[p.id]:
                    self.db.execute("INSERT INTO macros VALUES (?,?,?)", (p.id, m.name, m.model_copy(
                        update={"approved": False, "enabled": False, "reviewed": False}).model_dump_json()))
            self.db.execute("DELETE FROM settings WHERE key='selected'")


class Credentials:
    """OS credential vault, excluded from SQLite, exports and diagnostic messages."""

    @staticmethod
    def get(printer_id):
        import keyring
        return keyring.get_password("KlippyAssistant", printer_id)

    @staticmethod
    def set(printer_id, secret):
        import keyring
        if secret:
            keyring.set_password("KlippyAssistant", printer_id, secret)
        else:
            try:
                keyring.delete_password("KlippyAssistant", printer_id)
            except keyring.errors.PasswordDeleteError:
                pass
