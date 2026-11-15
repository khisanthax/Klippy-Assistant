import json
import threading
import time
from types import SimpleNamespace

import numpy as np
from PySide6.QtWidgets import QApplication

from klippy.history import InteractionHistory
from klippy.history_ui import HistoryPage
from klippy.session import Session
from klippy.voice import VoiceLoop


def test_countdown_waits_for_actual_render_and_echo_tail_with_long_generation_delay():
    clock = [100.0]
    session = Session(lambda: clock[0], 17)
    session.touch()
    entered, release = threading.Event(), threading.Event()

    def synthesize(*args, **kwargs):
        entered.set()
        release.wait(3)
        return SimpleNamespace(samples=np.full(320, 0.1, np.float32), sample_rate=16000)

    delivered = []
    voice = VoiceLoop(
        SimpleNamespace(synthesize=synthesize),
        lambda _: None,
        lambda _: None,
        session=session,
        clock=lambda: clock[0],
        on_delivery=lambda *v: delivered.append(v),
    )
    worker = threading.Thread(target=voice._speak)
    worker.start()
    try:
        voice.say("Synthetic response", token="review")
        assert entered.wait(2)
        clock[0] += 90
        assert not session.snapshot()["ready"] and session.until == float("inf")
        release.set()
        deadline = time.monotonic() + 3
        while not voice.playback.remaining and time.monotonic() < deadline:
            time.sleep(0.005)
        voice._render(320)
        assert not session.snapshot()["ready"]  # DAC/echo tail has not completed.
        while not delivered and time.monotonic() < deadline:
            time.sleep(0.01)
        assert delivered == [("review", True)]
        assert session.snapshot()["ready"] and session.snapshot()["remaining"] == 17
    finally:
        release.set()
        voice.close()
        worker.join(2)


def test_muted_inflight_asr_logs_discard_code_but_never_the_late_transcript(rig):
    h = InteractionHistory(rig[0])
    h.configure(enabled=True, transcripts=True)
    entered, release = threading.Event(), threading.Event()

    def transcribe(_):
        entered.set()
        release.wait(3)
        return "Klippy synthetic private words"

    heard = []
    voice = VoiceLoop(
        SimpleNamespace(transcribe=transcribe, reset_wake=lambda: None),
        heard.append,
        lambda _: None,
        history=h,
    )
    voice.enabled.set()
    try:
        voice._transcribe(np.full(1600, 0.1, np.float32), voice.epoch, True, False)
        assert entered.wait(2)
        voice.enabled.clear()
        voice.reset_session()
        release.set()
        voice.asr_pool.submit(lambda: None).result(timeout=3)
        assert not heard and "synthetic private words" not in json.dumps(h.entries())
        assert any(
            row.get("diagnostic") == "input_generation_invalid" and row["outcome"] == "canceled"
            for row in h.entries()
        )
    finally:
        release.set()
        voice.close()
        h.close()


def test_history_controls_filters_selection_details_and_export(rig, tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    h = InteractionHistory(rig[0])
    page = HistoryPage(h, rig[0])
    try:
        assert not page.controls["enabled"].isChecked()
        page.configure(enabled=True, transcripts=True, responses=True)
        assert page.controls["enabled"].isChecked() and page.controls["transcripts"].isChecked()
        h.record(
            "input",
            trace=1,
            printer_id="sim",
            printer="Test Printer",
            user_transcript="synthetic hello",
            response="synthetic reply",
            outcome="success",
        )
        h.record("failed", trace=2, printer_id="sim", outcome="failed")
        page.outcome.setCurrentText("failed")
        page.reload()
        assert len(page.rows) == 1 and page.rows[0]["outcome"] == "failed"
        page.outcome.setCurrentIndex(0)
        page.reload()
        page.table.selectRow(0)
        page.details()
        assert "outcome" in page.detail.toPlainText()
        path = tmp_path / "selected.json"
        monkeypatch.setattr("klippy.history_ui.QFileDialog.getSaveFileName", lambda *a: (str(path), ""))
        page.export(True)
        assert len(json.loads(path.read_text())["entries"]) == 1
        page.configure(transcripts=False, responses=False)
        assert "Transcript text disabled" in page.notice.text()
        assert all("user_transcript" not in row and "response" not in row for row in page.rows)
    finally:
        page.timer.stop()
        page.close()
        page.deleteLater()
        app.processEvents()
        h.close()


def test_history_view_is_bounded_but_filtered_export_contains_all_matches(rig, tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    h = InteractionHistory(rig[0])
    h.configure(enabled=True)
    for trace in range(205):
        h.record("input", trace=trace, printer_id="sim")
    page = HistoryPage(h, rig[0])
    try:
        assert page.table.rowCount() == 200
        path = tmp_path / "all-filtered.json"
        monkeypatch.setattr("klippy.history_ui.QFileDialog.getSaveFileName", lambda *a: (str(path), ""))
        page.export(False)
        assert len(json.loads(path.read_text())["entries"]) == 205
    finally:
        page.timer.stop()
        page.close()
        page.deleteLater()
        app.processEvents()
        h.close()


def test_mute_revokes_capture_before_any_history_observer_runs(rig, monkeypatch):
    from klippy.app import Window

    app = QApplication.instance() or QApplication([])
    window = Window(rig[0], smoke=True)
    window.timer.stop()
    voice = VoiceLoop(
        SimpleNamespace(reset_wake=lambda: None),
        lambda _: None,
        lambda _: None,
        session=window.conversation.session,
    )
    window.voice = voice
    voice.enabled.set()
    voice.session.touch()
    rig[0].set("listening", {"mode": "always"})
    observed = []
    monkeypatch.setattr(window.history, "record", lambda *a, **k: observed.append(voice.enabled.is_set()))
    try:
        window.toggle_listening()
        assert observed and not any(observed) and voice.listen_until == 0
    finally:
        window.quit()
        window.deleteLater()
        app.processEvents()


def test_failed_session_observer_cannot_prevent_clearing_authorization():
    session = Session()
    session.touch()
    session.begin()

    def broken(*args):
        raise OSError("Synthetic history storage fault")

    session.on_event = broken
    session.clear("muted")
    assert session.until == 0 and not session.holds and session.session_id is None


async def test_failed_history_hook_never_changes_safety_validation_or_cancellation(rig):
    from klippy.conversation import Conversation

    class Broken:
        def record(self, *args, **kwargs):
            raise OSError("Synthetic log failure")

    engine = rig[2]
    engine.history = Broken()
    c = Conversation(engine)
    assert "Confirm" in await c.hear("home")
    c.clear("muted")
    assert engine.pending is None and not rig[1].writes
