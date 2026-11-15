"""Synthetic ASR outputs and memory-only audio; no owner recordings or printer connections."""
import json
import os
from types import SimpleNamespace

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from klippy.app import Window
from klippy.audio import RATE
from klippy.voice import SherpaBackend, VoiceLoop, VoiceState
from klippy.voice_diagnostics import definition


@pytest.fixture
def window(rig):
    app = QApplication.instance() or QApplication([])
    value = Window(rig[0], smoke=True)
    value.timer.stop()
    value.history.configure(enabled=True, transcripts=True, responses=True)
    states = []
    backend = SimpleNamespace(transcribe=lambda samples: "Hey, Cuppy.", reset_wake=lambda: None)
    voice = VoiceLoop(backend, lambda text: None, states.append, session=value.conversation.session,
                      history=value.history)
    value.voice = voice
    voice.enabled.set()
    voice.capture_ready.set()
    yield value, voice, states
    value.quit()
    value.deleteLater()
    app.processEvents()


def test_exact_rejected_wake_attention_chain_and_copy(window, rig):
    value, voice, states = window
    voice.wake_attempt = "synthetic_attempt"
    voice.report_state("Checking wake word")
    voice._transcribe(np.full(RATE, .05, np.float32), voice.epoch, True, False)
    voice.asr_pool.submit(lambda: None).result(timeout=4)
    for state in states:
        value.result("voice_state", state)
    assert value.sprite.state == "error"
    assert "Wake phrase wasn't recognized" in value.sprite.toolTip()
    assert voice.session.until == 0 and value.engine.pending is None and not rig[1].writes
    copied = value.history_page.copy_latest_diagnostic()
    assert copied["diagnostic"] == "wake_prefix_rejected"
    assert copied["voice_stage"] == "wake_verification"
    assert copied["user_transcript"] == "Hey, Cuppy."
    assert copied["attempt_id"] == "synthetic_attempt" and copied["session_state"] == "not_opened"
    assert copied["diagnostic_timestamp"] > 0 and copied["event_id"]
    assert json.loads(QApplication.clipboard().text()) == copied
    assert any(e.get("orb_to") == "error" for row in value.history.entries() for e in row.get("voice_events", []))


def test_new_wake_clears_previous_attention_and_stale_errors_cannot_restore_it(window):
    value, voice, _ = window
    old = VoiceState("Wake transcript unclear", voice.epoch, voice.state_token)
    value.result("voice_state", old)
    assert value.sprite.state == "error"
    voice.interrupt()
    value.result("voice_wake", voice.epoch)
    assert value.sprite.state == "verifying"
    value.result("voice_state", old)
    assert value.sprite.state == "verifying"
    value.result("voice_state", VoiceState("Wake transcript unclear", voice.epoch, object()))
    assert value.sprite.state == "verifying"
    rows = [e for row in value.history.entries() for e in row.get("voice_events", [])]
    assert {"stale_owner", "stale_generation"} <= {e.get("event_status") for e in rows}


def test_muted_asr_error_does_not_trigger_attention(window):
    value, voice, _ = window
    voice.enabled.clear()
    value.result("voice_state", VoiceState("Speech recognition unavailable; no request sent", voice.epoch, voice.state_token))
    assert value.sprite.state != "error"
    assert any(e.get("event_status") == "muted" for row in value.history.entries() for e in row.get("voice_events", []))


@pytest.mark.parametrize("text,code,stage", [
    ("Speech recognition unavailable; no request sent", "asr_unavailable", "asr"),
    ("Speech recognition unavailable", "asr_unavailable", "asr"),
    ("Microphone or speaker unavailable; retrying safely", "audio_device_unavailable", "device"),
    ("Speaker or speech model unavailable; text remains accessible", "tts_unavailable", "tts"),
    ("Audio discontinuity", "audio_discontinuity", "capture"),
])
def test_failures_have_distinct_stage_and_reason(window, text, code, stage):
    value, voice, _ = window
    value.result("voice_state", VoiceState(text, voice.epoch, voice.state_token))
    assert value.sprite.state == "error"
    copied = value.sprite.copy_latest_diagnostic()
    assert copied["diagnostic"] == code and copied["voice_stage"] == stage
    assert value.sprite.toolTip() == copied["reason"]


def test_consent_revocation_removes_nested_transcripts_and_copy_text(window):
    value, voice, _ = window
    value.history.record("asr", trace=999, user_transcript="Hey Cuppy", verification_transcript="Klippy")
    state = VoiceState("Wake transcript unclear", voice.epoch, voice.state_token, trace=999)
    value.result("voice_state", state)
    assert value.latest_voice_diagnostic()["user_transcript"] == "Hey Cuppy"
    value.history.configure(transcripts=False)
    assert "transcript" not in json.dumps(value.latest_voice_diagnostic())
    assert "Hey Cuppy" not in json.dumps(value.history.entries())
    value.history.configure(enabled=False)
    assert "transcript" not in json.dumps(value.sprite.copy_latest_diagnostic())


def test_arbitrary_status_words_do_not_classify_attention(window):
    value, _, _ = window
    value.sprite.pipeline_event("The printer is fully homed; no failed requests")
    assert value.sprite.state != "error" and definition("The buffer is full") is None


@pytest.mark.parametrize("results,expected", [
    (["Hey Klippy", "Klippy."], True),
    (["Hey Cuppy", "Klippy"], False),
    (["Klippy", "Hey Crippy"], False),
    (["Klippy", "Klippy heat to 90"], False),
    (["confirm", "Klippy"], False),
])
def test_two_strict_wake_only_redecodes_required(results, expected):
    backend = object.__new__(SherpaBackend)
    backend.strict_wake = lambda samples: True
    calls = []
    def transcribe(samples):
        calls.append(samples)
        return results[len(calls)-1]
    backend.transcribe = transcribe
    original = np.full(RATE, .05, np.float32)
    result = backend.verify_short_wake(original, lambda: False)
    assert bool(result) is expected
    for samples in calls:
        assert np.count_nonzero(samples) == len(original)  # Only silence is added.
    assert len(calls) <= 2


def test_redecode_cancellation_and_long_input_are_rejected():
    backend = object.__new__(SherpaBackend)
    backend.strict_wake = lambda samples: True
    backend.transcribe = lambda samples: (_ for _ in ()).throw(AssertionError("Must not decode"))
    assert backend.verify_short_wake(np.ones(RATE), lambda: True) is None
    assert backend.verify_short_wake(np.ones(4*RATE), lambda: False) is None


def test_recovered_short_wake_forwards_no_command_or_confirmation(window):
    value, voice, states = window
    texts = iter(["Hey Cuppy", "Hey Klippy", "Klippy."])
    backend = object.__new__(SherpaBackend)
    backend.strict_wake = lambda samples: True
    backend.transcribe = lambda samples: next(texts)
    backend.reset_wake = lambda: None
    voice.backend = backend
    inputs = []
    voice.on_text = inputs.append
    voice._transcribe(np.ones(RATE, np.float32)*.05, voice.epoch, True, False, "old_confirmation")
    voice.asr_pool.submit(lambda: None).result(timeout=4)
    assert len(inputs) == 1 and inputs[0].text.strip() == "Klippy"
    assert inputs[0].confirmation_token is None and inputs[0].woke
    assert value.engine.pending is None and not any("unclear" in s for s in states)


def test_unresolved_redecode_stays_rejected_and_cannot_open_session(window):
    value, voice, _ = window
    voice.backend.verify_short_wake = lambda samples, cancelled: "Klippy heat to 90"
    inputs = []
    voice.on_text = inputs.append
    voice._transcribe(np.ones(RATE, np.float32)*.05, voice.epoch, True, False)
    voice.asr_pool.submit(lambda: None).result(timeout=4)
    assert not inputs and voice.session.until == 0 and value.engine.pending is None


def test_empty_asr_is_distinct_from_a_stale_or_unrecognized_prefix(window):
    value, voice, states = window
    voice.backend.transcribe = lambda samples: ""
    voice._transcribe(np.ones(RATE, np.float32), voice.epoch, True, False)
    voice.asr_pool.submit(lambda: None).result(timeout=4)
    for state in states:
        value.result("voice_state", state)
    assert value.sprite.latest_diagnostic["diagnostic"] == "asr_empty"
    assert value.sprite.state == "error" and voice.session.until == 0


def test_redecode_interruption_cannot_restore_session_or_deliver_input(window):
    value, voice, _ = window
    inputs = []
    voice.on_text = inputs.append
    def verifier(samples, cancelled):
        voice.interrupt()
        assert cancelled()
        return "Klippy"
    voice.backend.verify_short_wake = verifier
    voice._transcribe(np.ones(RATE, np.float32), voice.epoch, True, False)
    voice.asr_pool.submit(lambda: None).result(timeout=4)
    assert not inputs and voice.session.until == 0 and value.engine.pending is None


def test_copy_when_no_diagnostic_never_leaves_unrelated_clipboard_text(window):
    value, _, _ = window
    QApplication.clipboard().setText("unrelated prior clipboard")
    result = value.sprite.copy_latest_diagnostic()
    assert result["diagnostic"] == "none_available"
    assert "unrelated" not in QApplication.clipboard().text()


def test_barge_in_rejection_does_not_use_short_wake_recheck(window):
    _, voice, _ = window
    voice.backend.verify_short_wake = lambda *args: (_ for _ in ()).throw(AssertionError("No echo recheck"))
    inputs = []
    voice.on_text = inputs.append
    voice._transcribe(np.ones(RATE, np.float32), voice.epoch, True, True)
    voice.asr_pool.submit(lambda: None).result(timeout=4)
    assert not inputs and voice.wake_diagnostics()["prefix_rejected"] == 1


def test_event_counts_exclude_arbitrary_fields_and_credentials(window):
    value, _, _ = window
    value.history.record("voice_diagnostic", diagnostic="asr_unavailable", event_status="accepted",
                         diagnostic_timestamp=123, voice_stage="asr",
                         wake_counts={"candidates": 2, "prefix_rejected": 1, "token": "not allowed"})
    result = value.history.latest_diagnostic()
    assert result["wake_counts"] == {"candidates": 2, "prefix_rejected": 1}
    assert "token" not in json.dumps(result)


def test_plain_verified_wake_never_carries_a_pending_confirmation_token(window):
    _, voice, _ = window
    inputs = []
    voice.backend.transcribe = lambda samples: "Hey Klippy."
    voice.on_text = inputs.append
    voice._transcribe(np.ones(RATE, np.float32), voice.epoch, True, False, "previous_confirmation")
    voice.asr_pool.submit(lambda: None).result(timeout=4)
    assert len(inputs) == 1 and inputs[0].text.strip() == "Klippy" and inputs[0].confirmation_token is None


def test_recheck_requires_strict_phonetic_evidence_before_asr():
    backend = object.__new__(SherpaBackend)
    backend.strict_wake = lambda samples: False
    backend.transcribe = lambda samples: (_ for _ in ()).throw(AssertionError("Unverified phonetics"))
    assert backend.verify_short_wake(np.ones(RATE, np.float32), lambda: False) is None


def test_copy_legacy_diagnostic_labels_unknown_session_and_honors_current_consent(window):
    value, _, _ = window
    value.history.record("wake_rejected", diagnostic="wake_prefix_rejected", user_transcript="synthetic rejected wake")
    copied = value.latest_voice_diagnostic()
    assert copied["event_status"] == "legacy_record" and copied["session_state"] == "unknown"
    assert copied["user_transcript"] == "synthetic rejected wake"
    prefs = value.history.prefs.model_dump()
    prefs["transcripts"] = False
    value.store.set("conversation_log", prefs)
    assert "user_transcript" not in value.latest_voice_diagnostic()


def test_dsp_discontinuity_invalidates_inflight_asr_before_it_can_reopen_session(window):
    import threading
    _, voice, _ = window
    entered, release = threading.Event(), threading.Event()
    inputs = []
    voice.on_text = inputs.append
    def delayed(samples):
        entered.set()
        release.wait(2)
        return "Klippy heat the nozzle to 90"
    voice.backend.transcribe = delayed
    voice._transcribe(np.ones(RATE, np.float32), voice.epoch, True, False)
    assert entered.wait(1)
    try:
        voice._reset_dsp()
    finally:
        release.set()
    voice.asr_pool.submit(lambda: None).result(timeout=4)
    assert not inputs and voice.session.until == 0
