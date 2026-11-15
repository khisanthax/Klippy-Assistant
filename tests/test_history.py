import json

import numpy as np
import pytest

from klippy.conversation import Conversation
from klippy.diagnostics import current, timings
from klippy.history import InteractionHistory


def test_default_does_not_create_log_or_persist_any_text(rig):
    history = InteractionHistory(rig[0])
    history.record("input", user_transcript="private synthetic utterance", response="synthetic reply")
    assert history.entries() == [] and not history.path.exists()


@pytest.mark.parametrize(
    "transcripts,responses,timing",
    [(False, False, False), (True, False, True), (False, True, True), (True, True, False)],
)
def test_text_and_timing_consent_are_independent(rig, transcripts, responses, timing):
    h = InteractionHistory(rig[0])
    try:
        h.configure(enabled=True, transcripts=transcripts, responses=responses, timing=timing)
        h.record(
            "input",
            trace=1,
            user_transcript="synthetic input",
            normalized_request="normalized",
            response="reply",
            spoken_response="spoken",
            milliseconds={"asr": 12},
        )
        row = h.entries()[0]
        assert ("user_transcript" in row) == transcripts and ("normalized_request" in row) == transcripts
        assert ("response" in row) == responses and ("spoken_response" in row) == responses
        assert ("milliseconds" in row) == timing
        h.configure(enabled=False)
        h.record("input", trace=2)
        assert len(h.entries()) == 1
    finally:
        h.close()


def test_retention_entry_bound_and_filters_apply_even_after_disable(rig):
    clock = [1000000.0]
    h = InteractionHistory(rig[0], clock=lambda: clock[0])
    try:
        h.configure(enabled=True, max_entries=2, retention_days=1)
        for i in range(3):
            h.record("input", trace=i, printer_id=str(i), outcome="failed" if i == 2 else "success")
            clock[0] += 1
        assert len(h.entries()) == 2 and len(h.entries(printer="2", outcome="failed", since=1000001)) == 1
        h.configure(enabled=False)
        clock[0] += 86401
        assert h.entries() == []
    finally:
        h.close()


def test_export_redacts_secrets_endpoints_and_never_accepts_audio(rig, tmp_path):
    h = InteractionHistory(rig[0])
    try:
        h.configure(enabled=True, transcripts=True, responses=True)
        h.record(
            "input",
            trace=1,
            user_transcript="password: secretExample token abcDefTest https://user:pw@example.test/private 192.168.1.25:7125",
            response="Bearer abcTokenValue " + ("Z" * 32),
            credentials="private",
            confirmation_token="private",
            audio=np.zeros(160),
            pcm=b"audio bytes",
            parameters={"heater": 0, "temperature": 90, "token": "secret"},
        )
        h.record("input", trace=2)
        path = tmp_path / "export.json"
        h.export(path, ids={h.entries()[-1]["id"]})
        data = json.loads(path.read_text())
        text = path.read_text()
        assert data["schema_version"] == 1 and len(data["entries"]) == 1
        for value in [
            "secretExample",
            "abcDefTest",
            "user:pw",
            "example.test",
            "192.168.1.25",
            "abcTokenValue",
            "Z" * 32,
            "audio bytes",
            "credentials",
            "confirmation_token",
        ]:
            assert value not in text
        assert data["entries"][0]["parameters"] == {"heater": 0, "temperature": 90}
    finally:
        h.close()


def test_revoking_text_removes_existing_fields_and_clear_truncates_wal(rig):
    h = InteractionHistory(rig[0])
    try:
        h.configure(enabled=True, transcripts=True, responses=True)
        h.record(
            "input", user_transcript="uniquely synthetic private words", response="private synthetic response"
        )
        h.configure(transcripts=False, responses=False, timing=False)
        assert "user_transcript" not in h.entries()[0] and "response" not in h.entries()[0]
        assert b"uniquely synthetic" not in h.path.read_bytes()
        h.clear()
        assert h.entries() == []
        assert not h.path.with_name(h.path.name + "-wal").stat().st_size
    finally:
        h.close()


def test_partial_timings_and_corrupt_history_fail_without_affecting_control(rig):
    h = InteractionHistory(rig[0])
    h.configure(enabled=True)
    h.path.write_bytes(b"not a database")
    assert h.record("input", milliseconds={"asr": float("nan"), "bad-key": 3}) is None
    assert h.entries() == [] and h.error == "history_storage_unavailable"
    h.close()


async def test_multiple_turns_and_canceled_expired_actions_are_explicit(rig):
    store, sim, engine, clock = rig
    h = InteractionHistory(store)
    h.configure(enabled=True)
    engine.history = h
    c = Conversation(engine, clock=lambda: clock[0])
    try:
        await c.hear("Klippy home")
        await c.hear("no")
        assert any(r["outcome"] == "canceled" and r.get("intent") == "home" for r in h.entries())
        ids = {r.get("session_id") for r in h.entries()}
        assert len(ids) == 1
        await c.hear("home")
        clock[0] += 40
        engine.cancel("expired")
        assert any(r["outcome"] == "expired" for r in h.entries()) and not sim.writes
    finally:
        h.close()


def test_timing_update_keeps_identity_and_does_not_create_old_rows(rig):
    h = InteractionHistory(rig[0])
    h.configure(enabled=True)
    try:
        trace = timings.new()
        context = current.set(trace)
        h.record("input", session_id="session-a")
        current.reset(context)
        timings.duration("asr", 0.01, trace)
        h.update_timings(timings.snapshot())
        row = h.entries()[0]
        assert row["milliseconds"]["asr"] == 10 and row["session_id"] == "session-a"
        assert len(h.entries()) == 1
    finally:
        h.close()


def test_database_uses_wal_and_reopens_committed_rows(rig):
    h = InteractionHistory(rig[0])
    h.configure(enabled=True)
    h.record("input")
    assert h.db.execute("pragma journal_mode").fetchone()[0] == "wal"
    h.close()
    h = InteractionHistory(rig[0])
    assert len(h.entries()) == 1
    h.close()
