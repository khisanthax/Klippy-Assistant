import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from klippy.app import Window  # noqa: E402
from klippy.domain import Action, Intent  # noqa: E402


class Voice:
    def __init__(self):
        self.jobs = []
        self.interruptions = 0

    def say(self, text, **kwargs):
        self.jobs.append(kwargs)

    def interrupt(self):
        self.interruptions += 1

    def close(self):
        pass


@pytest.fixture
def window(rig):
    app = QApplication.instance() or QApplication([])
    value = Window(rig[0], smoke=True)
    value.engine = rig[2]
    value.conversation.engine = rig[2]
    value.voice = Voice()
    yield value
    value.quit()
    value.deleteLater()
    app.processEvents()


async def test_notification_cannot_arm_another_pending_prompt(window, rig):
    _, sim, engine, _ = rig
    prompt = await engine.propose(Intent(action=Action.HOME, printer_id="sim"), defer_confirmation=True)
    token = engine.pending.token
    window.say("Unrelated printer alert")
    assert not window.voice.jobs  # Fault speech must not consume the response window.
    assert not engine.pending.ready
    window.say(prompt, confirmation=True)
    assert window.voice.jobs[-1]["token"] == token
    assert not engine.pending.ready and not sim.writes


async def test_muting_inflight_prompt_cancels_and_text_only_prompt_arms(window, rig):
    _, sim, engine, _ = rig
    intent = Intent(action=Action.HOME, printer_id="sim")
    await engine.propose(intent, defer_confirmation=True)
    window.spoken.setChecked(False)
    assert engine.pending is None
    prompt = await engine.propose(intent, defer_confirmation=True)
    window.say(prompt, confirmation=True)
    assert engine.pending.ready and not sim.writes


@pytest.mark.parametrize("verified", [False, True])
def test_local_heater_limit_review_requires_explicit_verified_checkbox(window, rig, monkeypatch, verified):
    from PySide6.QtWidgets import QCheckBox, QDialog, QDoubleSpinBox
    store, sim, _, _ = rig
    def review(dialog):
        for spin in dialog.findChildren(QDoubleSpinBox):
            spin.setValue(180)
        dialog.findChild(QCheckBox).setChecked(verified)
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(QDialog, "exec", review)
    window.review_heater_limits()
    assert store.get("heater_limits", {}) == ({"sim": {"0": 180.0, "1": 180.0}} if verified else {})
    assert not sim.writes


def test_new_command_stops_stale_speech_before_interpretation(window, monkeypatch):
    def submit(name, coroutine):
        coroutine.close()
    monkeypatch.setattr(window.worker, "submit", submit)
    before = window.voice.interruptions
    window.submit_turn("status")
    assert window.voice.interruptions == before + 1


async def test_spoken_presentation_never_replaces_pending_exact_review(window, rig):
    from klippy.presentation import Response
    spoken = []
    window.voice.say = lambda text, **kwargs: spoken.append((text, kwargs))
    window.say(Response("205.5 degrees", "206 degrees"))
    assert spoken[-1][0] == "206 degrees"
    prompt = await rig[2].propose(Intent(action=Action.HOME, printer_id="sim"), defer_confirmation=True)
    window.say(Response(prompt, "Unsafe summary"), confirmation=True)
    assert spoken[-1][0] == prompt and spoken[-1][1]["token"] == rig[2].pending.token


def test_printer_page_exposes_edit_and_editor_persists_names(window, rig, monkeypatch):
    from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit, QPushButton, QTextEdit
    assert any(b.text() == "Edit Names & Aliases" for b in window.findChildren(QPushButton))
    window.fleet.selectRow(0)
    def edit(dialog):
        fields = dialog.findChildren(QLineEdit)
        fields[0].setText("Mercury One")
        dialog.findChild(QTextEdit).setPlainText("M1\nMercury 1")
        fields[1].setText("Switch to M1")
        next(b for b in dialog.findChildren(QPushButton) if b.text().startswith("Test name")).click()
        dialog.findChild(QDialogButtonBox).accepted.emit()
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(QDialog, "exec", edit)
    window.edit_printer_aliases()
    assert rig[0].printers()[0].name == "Mercury One"
    assert rig[0].printers()[0].aliases == ("M1", "Mercury 1")
    assert window.active_name() == "Mercury One" and not rig[1].writes


def test_loaded_voice_is_enabled_before_workers_start(window, rig, monkeypatch):
    import threading

    from klippy.voice import VoiceLoop
    rig[0].set("listening", {"mode": "always"})
    started = []
    class LoadedVoice:
        def __init__(self, *args, **kwargs):
            self.enabled = threading.Event()
        def start(self):
            started.append(self.enabled.is_set())
        def close(self):
            pass
    monkeypatch.setattr("klippy.voice.VoiceLoop", LoadedVoice)
    window.result("voice_loaded", (object(), None))
    assert started == [True]
    assert VoiceLoop is not LoadedVoice  # Test never opens a physical microphone.


async def test_interpretation_diagnostic_is_kept_out_of_normal_speech(window, monkeypatch):
    from klippy.diagnostics import timings
    from klippy.safety import Rejected
    requests, spoken = [], []
    monkeypatch.setattr(window.worker, "submit", lambda name, coroutine: requests.append(coroutine))
    async def reject(*args, **kwargs):
        raise Rejected("Please restate the heater and target temperature.", code="intent_parameters_for_temperatures")
    monkeypatch.setattr(window.conversation, "hear", reject)
    window.voice.say = lambda text, **kwargs: spoken.append(text)
    window.submit_turn("adjust the nozzle")
    result = await requests.pop()
    window.result("turn", result)
    assert spoken == ["Please restate the heater and target temperature."]
    reaction = next(row for row in timings.snapshot() if row["reaction"] == window.reaction_trace)
    assert reaction["error_code"] == "intent_parameters_for_temperatures"
    assert "intent_parameters_for_temperatures" in timings.compact()


async def test_cancel_stops_prompt_and_invalidates_its_token(window, rig):
    _, sim, engine, _ = rig
    await engine.propose(Intent(action=Action.HOME, printer_id="sim"), defer_confirmation=True)
    window.cancel()
    assert engine.pending is None and window.voice.interruptions == 1
    assert not sim.writes


async def test_reaction_measurement_cannot_speak_over_pending_confirmation(window, rig, monkeypatch):
    _, sim, engine, _ = rig
    await engine.propose(Intent(action=Action.HOME, printer_id="sim"), defer_confirmation=True)
    monkeypatch.setattr(window.worker, "submit", lambda *args: pytest.fail("Started reaction during confirmation"))
    window.reaction_test()
    window.result("reaction", (None, "Simulated temperatures"))
    assert not window.voice.jobs and not engine.pending.ready and not sim.writes
