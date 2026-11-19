"""Seed v0.7.2-shaped synthetic profiles. Verification never creates a database."""
import argparse
import hashlib
import json
import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path

PRINTER = "qa-simulation"
HISTORY_ID = "qa-preservation:1"
SETTINGS = {
    "selected": PRINTER, "response_style": "detailed", "qa_sentinel": "preserve-me",
    "printer_limit_overrides": {PRINTER: {"axes": {"x": {"position_max": 200}}}},
    "heater_limits": {PRINTER: {"0": 80, "1": 100}},
    "voice_orb": {"diameter": 256, "position": "custom", "custom_position": [40, 50], "animations": False},
}
# SQL and record fields taken from the v0.7.2-preview.1 tag, independent of current Store.
SCHEMA = """
CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE printers(id TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE macros(printer TEXT, name TEXT, value TEXT NOT NULL, PRIMARY KEY(printer,name));
CREATE TABLE events(id INTEGER PRIMARY KEY, timestamp TEXT DEFAULT CURRENT_TIMESTAMP, printer TEXT, code TEXT);
"""


def prepare(profile, consent):
    profile.mkdir(parents=True, exist_ok=False)
    with closing(sqlite3.connect(profile / "settings.sqlite")) as db, db:
        db.executescript(SCHEMA)
        prefs = dict(SETTINGS, conversation_log={"enabled": consent, "transcripts": consent, "responses": consent,
                                                 "timing": True, "retention_days": 7, "max_entries": 1000})
        db.executemany("INSERT INTO settings VALUES (?,?)", [(k, json.dumps(v)) for k, v in prefs.items()])
        printer = dict(id=PRINTER, name="QA simulation", aliases=["QA One", "Q1"],
                       url="http://127.0.0.1:17125", approved=True)
        db.execute("INSERT INTO printers VALUES (?,?)", (PRINTER, json.dumps(printer)))
        macro = dict(name="QA_STATUS", definition="M105", approved=True, reviewed=True, enabled=True)
        db.execute("INSERT INTO macros VALUES (?,?,?)", (PRINTER, "QA_STATUS", json.dumps(macro)))
    if consent:
        with closing(sqlite3.connect(profile / "conversation-history.sqlite")) as db, db:
            db.execute("CREATE TABLE turns(id TEXT PRIMARY KEY, timestamp REAL, printer TEXT, outcome TEXT, data TEXT)")
            now = time.time()
            turn = dict(id=HISTORY_ID, timestamp=now, printer_id=PRINTER, outcome="answered",
                        user_transcript="Synthetic status question", response="Synthetic answer", events=[])
            db.execute("INSERT INTO turns VALUES (?,?,?,?,?)", (HISTORY_ID, now, PRINTER, "answered", json.dumps(turn)))


def rows(path, query, args=()):
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("QA database integrity failure")
        return db.execute(query, args).fetchall()


def snapshot(profile, consent):
    settings = profile / "settings.sqlite"
    keys = sorted([*SETTINGS, "conversation_log"])
    table = rows(settings, "SELECT key,value FROM settings WHERE key IN (" +
                 ",".join("?" for _ in keys) + ") ORDER BY key", keys)
    history = profile / "conversation-history.sqlite"
    turns = rows(history, "SELECT * FROM turns WHERE id=?", (HISTORY_ID,)) if consent else []
    if not consent and history.exists() and rows(history, "SELECT id FROM turns"):
        raise ValueError("History stored with consent off")
    if len(table) != len(keys) or consent and len(turns) != 1:
        raise ValueError("Missing seeded QA record")
    contents = [table, rows(settings, "SELECT * FROM printers ORDER BY id"),
                rows(settings, "SELECT * FROM macros ORDER BY printer,name"), turns]
    return hashlib.sha256(json.dumps(contents).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "verify"))
    parser.add_argument("consent", choices=("on", "off"))
    args = parser.parse_args()
    base = Path(os.environ["LOCALAPPDATA"]).resolve()
    root = Path(__file__).resolve().parents[1] / "local" / "installer-qa"
    if base.parent != root.resolve() or not base.name.startswith("profile-" + args.consent + "-"):
        raise ValueError("Use an isolated installer QA profile")
    profile = base / "KlippyAssistant"
    receipt = root / (base.name + ".sha256")
    consent = args.consent == "on"
    if args.action == "prepare":
        prepare(profile, consent)
        receipt.write_text(snapshot(profile, consent))
    elif snapshot(profile, consent) != receipt.read_text():
        raise ValueError("Preserved profile differs from its pre-install receipt")


if __name__ == "__main__":
    main()
