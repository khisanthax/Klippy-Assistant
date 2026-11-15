"""Opt-in, bounded local troubleshooting records. Never accepts PCM or credentials."""

import json
import math
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path

from pydantic import Field

from .diagnostics import current
from .domain import StrictModel


class LogPreferences(StrictModel):
    enabled: bool = False
    transcripts: bool = False
    responses: bool = False
    timing: bool = True
    retention_days: int = Field(default=7, ge=1, le=30)
    max_entries: int = Field(default=1000, ge=1, le=10000)


def redact(value):
    text = str(value)[:4000]
    text = re.sub(
        r"https?://\S+|\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?", "[connection redacted]", text, flags=re.I
    )
    text = re.sub(
        r'(?i)\b(?:bearer\s+\S+|(?:password|passwd|secret|token|api[_ -]?key|authorization)\b["\s]*(?:is|[:=])?\s*["\s]*\S+)',
        "[secret redacted]",
        text,
    )
    return re.sub(r"\b[A-Za-z0-9_-]{24,}\b", "[token redacted]", text)


class InteractionHistory:
    def __init__(self, store, clock=time.time):
        self.store, self.clock = store, clock
        self.path = store.path.with_name("conversation-history.sqlite")
        self.lock = threading.RLock()
        self.db = None
        self.run_id = uuid.uuid4().hex
        self.error = None

    @property
    def prefs(self):
        try:
            return LogPreferences.model_validate(self.store.get("conversation_log", {}))
        except (ValueError, TypeError,sqlite3.Error):
            return LogPreferences()

    def _open(self):
        if self.db is None:
            self.db = sqlite3.connect(self.path, check_same_thread=False, timeout=0.1)
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA secure_delete=ON")
            self.db.execute(
                "CREATE TABLE IF NOT EXISTS turns(id TEXT PRIMARY KEY, timestamp REAL, printer TEXT, outcome TEXT, data TEXT)"
            )
        return self.db

    def _prune(self, db):
        prefs = self.prefs
        db.execute("DELETE FROM turns WHERE timestamp < ?", (self.clock() - prefs.retention_days * 86400,))
        db.execute(
            "DELETE FROM turns WHERE id NOT IN (SELECT id FROM turns ORDER BY timestamp DESC,id DESC LIMIT ?)",
            (prefs.max_entries,),
        )

    def _clean(self, fields):
        prefs = self.prefs
        result = {}
        for key in (
            "session_id",
            "turn_id",
            "printer",
            "printer_id",
            "source",
            "intent",
            "query",
            "diagnostic",
            "reason",
        ):
            if isinstance(fields.get(key), (str, int)):
                if key in {"source", "intent", "query", "diagnostic", "reason"}:
                    result[key] = (
                        fields[key]
                        if isinstance(fields[key], str) and re.fullmatch(r"[A-Za-z0-9_]{1,80}", fields[key])
                        else "redacted_code"
                    )
                    continue
                result[key] = (
                    str(fields[key])[:128]
                    if key in {"session_id", "turn_id", "printer_id"}
                    else redact(fields[key])
                )
        for key in (
            "wake_detected",
            "clarification_requested",
            "confirmation_requested",
            "muted",
            "followup_active",
            "during_followup",
        ):
            if type(fields.get(key)) is bool:
                result[key] = fields[key]
        if prefs.transcripts:
            for key in ("user_transcript", "normalized_request"):
                if isinstance(fields.get(key), str):
                    result[key] = redact(fields[key])
        if prefs.responses:
            for key in ("response", "spoken_response"):
                if isinstance(fields.get(key), str):
                    result[key] = redact(fields[key])
        if prefs.timing and isinstance(fields.get("milliseconds"), dict):
            result["milliseconds"] = {
                k: round(v, 2)
                for k, v in fields["milliseconds"].items()
                if re.fullmatch(r"[a-z_]{1,60}", k) and type(v) in (int, float) and math.isfinite(v)
            }
        if isinstance(fields.get("parameters"), dict):
            result["parameters"] = {
                k: v
                for k, v in fields["parameters"].items()
                if re.fullmatch(r"[A-Za-z_]{1,40}", k)
                and type(v) in (float, int)
                and math.isfinite(v)
                and not re.search(r"token|secret|passw|credential|auth|key", k, re.I)
            }
        return result

    def record(self, event, *, trace=None, outcome=None, **fields):
        if not self.prefs.enabled:
            return None
        trace = current.get() if trace is None else trace
        if trace is not None and type(trace) is not int:
            return None
        identity = self.run_id + ":" + str(trace if trace is not None else uuid.uuid4().hex)
        try:
            with self.lock:
                db = self._open()
                with db:
                    row = db.execute("SELECT data FROM turns WHERE id=?", (identity,)).fetchone()
                    data = (
                        json.loads(row[0])
                        if row
                        else {"id": identity, "timestamp": self.clock(), "events": []}
                    )
                    cleaned = self._clean(fields)
                    if event == "input" and fields.get("source") == "voice" and "user_transcript" in data:
                        cleaned.pop("user_transcript", None)
                    data.update(cleaned)
                    if re.fullmatch(r"[a-z_]{1,60}", event):
                        if not data["events"] or data["events"][-1] != event:
                            data["events"] = [*data["events"], event][-32:]
                    if outcome in {
                        "success",
                        "clarification_needed",
                        "rejected",
                        "canceled",
                        "expired",
                        "executed",
                        "failed",
                        "proposed",
                        "confirmed",
                    }:
                        data["outcome"] = outcome
                    data.setdefault("outcome", "success")
                    db.execute(
                        "INSERT OR REPLACE INTO turns VALUES (?,?,?,?,?)",
                        (
                            identity,
                            data["timestamp"],
                            data.get("printer_id", ""),
                            data["outcome"],
                            json.dumps(data),
                        ),
                    )
                    self._prune(db)
            return identity
        except (sqlite3.Error, OSError, ValueError,TypeError):
            self.error = "history_storage_unavailable"
            return None  # Troubleshooting never changes command authority or retries a command.

    def update_timings(self, rows):
        if not self.prefs.enabled or not self.prefs.timing or self.db is None:
            return
        for row in rows:
            identity = self.run_id + ":" + str(row["reaction"])
            with self.lock:
                try:
                    exists = self.db.execute("SELECT 1 FROM turns WHERE id=?", (identity,)).fetchone()
                except sqlite3.Error:
                    self.error = "history_storage_unavailable"
                    return
            if exists:
                self.record(
                    "timing",
                    trace=row["reaction"],
                    milliseconds=row["milliseconds"],
                    diagnostic=row.get("error_code"),
                )

    def configure(self, **changes):
        prefs = LogPreferences.model_validate({**self.prefs.model_dump(), **changes})
        self.store.set("conversation_log", prefs.model_dump())
        # Revoking text/timing consent removes those fields from existing entries too.
        with self.lock:
            for data in self.entries():
                cleaned = {
                    **{k: data[k] for k in ("id", "timestamp", "events", "outcome")},
                    **self._clean(data),
                }
                with self.db:
                    self.db.execute("UPDATE turns SET data=? WHERE id=?", (json.dumps(cleaned), data["id"]))
            if self.db is not None:
                self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    def entries(self, *, printer=None, outcome=None, since=None, search=None, limit=None):
        with self.lock:
            if self.db is None and not self.path.exists():
                return []
            try:
                db = self._open()
                with db:
                    self._prune(db)
                clauses, params = [], []
                for key, value in [("printer", printer), ("outcome", outcome)]:
                    if value:
                        clauses.append(key + "=?")
                        params.append(value)
                if since is not None:
                    clauses.append("timestamp>=?")
                    params.append(since)
                if search:
                    clauses.append("LOWER(data) LIKE ?")
                    params.append("%" + search.lower() + "%")
                suffix = ""
                if limit is not None:
                    if type(limit) is not int or not 1 <= limit <= 10000:
                        raise ValueError("Invalid history limit")
                    suffix = " LIMIT ?"
                    params.append(limit)
                return [
                    json.loads(r[0])
                    for r in db.execute(
                        "SELECT data FROM turns"
                        + (" WHERE " + " AND ".join(clauses) if clauses else "")
                        + " ORDER BY timestamp DESC,id DESC"
                        + suffix,
                        params,
                    )
                ]
            except (sqlite3.Error, ValueError):
                self.error = "history_storage_unavailable"
                return []

    def export(self, path, ids=None, **filters):
        rows = self.entries(**filters)
        if ids is not None:
            rows = [r for r in rows if r["id"] in ids]
        Path(path).write_text(json.dumps({"schema_version": 1, "entries": rows}, indent=2), encoding="utf-8")

    def clear(self):
        with self.lock:
            if self.db is not None or self.path.exists():
                db = self._open()
                with db:
                    db.execute("DELETE FROM turns")
                db.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    def close(self):
        with self.lock:
            if self.db is not None:
                self.db.close()
                self.db = None
