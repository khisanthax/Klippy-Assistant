from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from functools import wraps
from pathlib import Path

from .domain import Macro, Printer


def serialized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self.lock:
            return method(self, *args, **kwargs)
    return call


def data_directory() -> Path:
    path = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share")) / "KlippyAssistant"
    path.mkdir(parents=True, exist_ok=True)
    return path


class Store:
    """Only settings/operational event codes are persisted. No utterance API exists."""

    def __init__(self, path: Path):
        self.path = path.resolve()
        self.lock = threading.RLock()
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

    @serialized
    def close(self):
        self.db.close()

    @serialized
    def get(self, key, default=None):
        row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    @serialized
    def set(self, key, value):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, json.dumps(value)))

    @serialized
    def printers(self):
        return [Printer.model_validate_json(r[0]) for r in self.db.execute("SELECT value FROM printers")]

    @serialized
    def save_printer(self, printer: Printer):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO printers VALUES (?,?)", (printer.id, printer.model_dump_json()))

    @serialized
    def remove_printer(self, printer_id):
        with self.db:
            self.db.execute("DELETE FROM macros WHERE printer=?", (printer_id,))
            self.db.execute("DELETE FROM printers WHERE id=?", (printer_id,))
            if self.get("selected") == printer_id:
                self.db.execute("DELETE FROM settings WHERE key='selected'")

    @serialized
    def macros(self, printer_id):
        return {m.name: m for (value,) in self.db.execute(
            "SELECT value FROM macros WHERE printer=?", (printer_id,)
        ) for m in [Macro.model_validate_json(value)]}

    @serialized
    def replace_macros(self, printer_id, macros):
        with self.db:
            self.db.execute("DELETE FROM macros WHERE printer=?", (printer_id,))
            self.db.executemany("INSERT INTO macros VALUES (?,?,?)", [
                (printer_id, m.name, m.model_dump_json()) for m in macros.values()
            ])

    @serialized
    def event(self, printer_id, code):
        allowed = {"disconnected", "connected", "fault", "mmu_fault", "paused", "command_sent", "outcome_unknown"}
        if code not in allowed:
            raise ValueError("Operational codes only")
        with self.db:
            self.db.execute("INSERT INTO events(printer,code) VALUES (?,?)", (printer_id, code))
            self.db.execute("DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT 1000)")

    @serialized
    def export(self, path: Path):
        # Macros/addresses are private user configuration. Never export credentials.
        payload = {"version": 2, "preferences": {key: self.get(key, default) for key, default in
                   (("followup_seconds", 30), ("confirmation_seconds", 30), ("spoken", True),
                    ("monitor_enabled", True), ("wake_threshold", .22))}, "printers": [p.model_dump(mode="json") for p in self.printers()],
                   "selected": self.get("selected"), "listening": self.get("listening", {}),
                   "macros": {p.id: [m.model_dump(mode="json") for m in self.macros(p.id).values()]
                              for p in self.printers()}}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @serialized
    def restore(self, path: Path):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") not in (1, 2):
            raise ValueError("Unsupported backup")
        printers = [Printer.model_validate_json(json.dumps(p)) for p in payload["printers"]]
        registries = {p.id: [Macro.model_validate_json(json.dumps(m)) for m in
                            payload.get("macros", {}).get(p.id, [])] for p in printers}
        if len({p.id for p in printers}) != len(printers):
            raise ValueError("Duplicate printer identifiers")
        for registry in registries.values():
            if len({m.name for m in registry}) != len(registry):
                raise ValueError("Duplicate macro names")
        preferences = payload.get("preferences", {})
        allowed = {"followup_seconds": (10, 120), "confirmation_seconds": (10, 120),
                   "wake_threshold": (.01, 1)}
        if not isinstance(preferences, dict) or set(preferences) - {*allowed, "spoken", "monitor_enabled"}:
            raise ValueError("Invalid preferences")
        for key, value in preferences.items():
            if key in allowed:
                low, high = allowed[key]
                if type(value) not in (int, float) or not low <= value <= high:
                    raise ValueError("Invalid preference range")
            elif type(value) is not bool:
                raise ValueError("Invalid preference type")
        # A SQLite online backup includes committed WAL pages before any mutation.
        backup = self.path.with_name(self.path.stem + ".before-restore-" + uuid.uuid4().hex[:12] + ".sqlite")
        destination = sqlite3.connect(backup)
        try:
            self.db.backup(destination)
        finally:
            destination.close()
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
            for key, value in preferences.items():
                self.db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, json.dumps(value)))
            # Heater bounds belong to a reviewed physical device, not a restored identifier.
            self.db.execute("DELETE FROM settings WHERE key='heater_limits'")
            # Recovery never silently restores immediate actions or an enabled microphone.
            self.db.execute("INSERT OR REPLACE INTO settings VALUES ('confirmations','{}')")
            self.db.execute("INSERT OR REPLACE INTO settings VALUES ('listening',?)",
                            (json.dumps({"mode": "manual", "enabled": False}),))
        return backup


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
