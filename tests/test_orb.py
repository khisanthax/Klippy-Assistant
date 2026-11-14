import json
import os
import threading
from types import SimpleNamespace

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRect, Qt  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from klippy.audio import AudioLevels  # noqa: E402
from klippy.orb import VoiceOrb  # noqa: E402
from klippy.orb_geometry import Desktop, Rect, native_to_logical, placement, safe_area, same_monitor  # noqa: E402
from klippy.orb_settings import preferences  # noqa: E402
from klippy.voice import VoiceLoop, VoiceState  # noqa: E402


@pytest.fixture
def orb(rig, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("klippy.orb.reduced_motion", lambda: False)
    clock, data = [100.0], {}
    value = VoiceOrb(lambda: None, rig[0], QIcon(), source=lambda: data, clock=lambda: clock[0])
    yield value, data, clock
    value.close()
    value.deleteLater()
    app.processEvents()


def test_hidden_idle_wake_verification_session_and_timeout(orb):
    value, data, clock = orb
    assert not value.isVisible() and not value.animation.isActive()
    data["microphone_ready"] = True
    value.pipeline_event("Checking wake word")
    assert value.isVisible() and value.state == "verifying"
    assert not data.get("session_active")  # Candidate grants no conversation authorization.
    data["session_active"] = True
    value.pipeline_event("Listening")
    assert value.state == "listening"
    clock[0] += 30
    value.refresh()
    assert value.isVisible()  # Existing session, not an independent orb deadline.
    data["session_active"] = False
    value.refresh()
    clock[0] += 3.1
    value.refresh()
    assert value.isVisible() and 0 < value.windowOpacity() < 1
    clock[0] += .21
    value.refresh()
    assert not value.isVisible() and not value.animation.isActive()


def test_microphone_disabled_is_never_listening_or_visible_unless_summoned(orb):
    value, data, clock = orb
    data.update(session_active=True, microphone_ready=False, microphone=.7)
    value.pipeline_event("Listening")
    assert value.state == "muted" and not value.isVisible() and value.last_levels[0] == 0
    value.summon()
    assert value.isVisible() and value.state == "muted"
    clock[0] += 3.1
    value.refresh()
    assert not value.isVisible()


def test_speaking_requires_rendered_pcm_and_interruption_clears_it(orb):
    value, data, _ = orb
    value.pipeline_event("Speaking")
    assert value.state == "thinking"  # Synthesizing/queued audio is not playback.
    data.update(playing=True, playback=.25)
    value.refresh()
    assert value.state == "speaking" and value.last_levels[1] == .25
    data["playing"] = False
    data["playback"] = 0
    value.clear_activity()
    assert value.state == "muted" and not any(value.playback)


def test_confirmation_persists_through_playback_until_engine_clears_it(orb):
    value, data, clock = orb
    data.update(pending=True, playing=True)
    value.refresh()
    assert value.state == "confirmation"
    clock[0] += 90
    data["playing"] = False
    value.refresh()
    assert value.state == "confirmation" and value.isVisible()
    data["pending"] = False
    value.clear_activity()
    assert value.state == "muted" and not value.isVisible()


@pytest.mark.parametrize("event", ["Speech recognition unavailable; no request sent", "Audio discontinuity", "Wake transcript unclear"])
def test_errors_end_thinking_and_are_brief(orb, event):
    value, data, clock = orb
    value.pipeline_event("Thinking")
    value.pipeline_event(event)
    assert value.state == "error"
    clock[0] += 2.6
    value.refresh()
    assert value.phase == "idle" and value.state == "muted" and not value.isVisible()


def test_lost_processing_event_has_bounded_attention_fallback(orb):
    value, _, clock = orb
    value.pipeline_event("Thinking")
    clock[0] += 96
    value.refresh()
    assert value.state == "error"
    clock[0] += 3
    value.refresh()
    assert value.state == "muted" and not value.isVisible()


def test_numeric_audio_peaks_expire_and_never_block_producer():
    clock = [100.0]
    levels = AudioLevels(lambda: clock[0])
    levels.publish("microphone", .4)
    levels.publish("microphone", .1)
    levels.publish("playback", .25, rendered=True)
    assert levels.snapshot() == {"microphone": .4, "playback": .25, "playing": True}
    assert levels.snapshot()["microphone"] == 0
    with levels.lock:
        levels.publish("microphone", 1)  # Try-lock drops this; no audio-thread wait.
    clock[0] += .3
    assert not any(levels.snapshot().values())
    levels.publish("playback", .5, rendered=True)
    levels.clear()
    assert not any(levels.snapshot().values())
    assert all(not isinstance(item, np.ndarray) for row in levels.values.values() for item in row)


def test_existing_voice_capture_and_render_drive_levels_without_opening_devices():
    backend = SimpleNamespace(wake=lambda samples: False, reset_wake=lambda: None)
    voice = VoiceLoop(backend, lambda _: None, lambda _: None)
    try:
        voice.enabled.set()
        near = np.full(160, .1, dtype=np.float32)
        voice.process_frame(near, np.zeros(160, dtype=np.float32), voice.clock())
        assert voice.levels.snapshot()["microphone"] > 0
        voice.playback.enqueue(near, voice.epoch)
        assert not voice.levels.snapshot()["playing"]
        assert np.any(voice._render(160))
        assert voice.levels.snapshot()["playing"]
        voice.interrupt()
        assert not any(voice.levels.snapshot().values())
        assert not voice.threads and not voice.capture_ready.is_set()
    finally:
        voice.close()


@pytest.mark.parametrize("interrupted", [False, True])
def test_synthesis_failure_reports_current_generation_and_never_interrupts_a_new_request(interrupted):
    entered, release, delivered = threading.Event(), threading.Event(), threading.Event()
    states = []
    def synthesize(*args, **kwargs):
        entered.set()
        release.wait(2)
        raise ValueError("synthetic TTS failure")
    voice = VoiceLoop(SimpleNamespace(synthesize=synthesize), lambda _: None, states.append,
                      on_delivery=lambda *args: delivered.set())
    worker = threading.Thread(target=voice._speak)
    worker.start()
    try:
        voice.say("Synthetic failure test")
        assert entered.wait(2)
        if interrupted:
            voice.interrupt()
        epoch = voice.epoch
        release.set()
        assert delivered.wait(2)
        errors = [state for state in states if "unavailable" in state]
        if interrupted:
            assert not errors and voice.epoch == epoch
        else:
            assert errors and errors[-1].epoch == voice.epoch
        assert not voice.playback.remaining
    finally:
        release.set()
        voice.close()
        worker.join(2)


@pytest.mark.parametrize("text", ["", "Klippy own speech"])
def test_rejected_asr_does_not_leave_processing_indicator_stuck(text):
    states, inputs = [], []
    voice = VoiceLoop(SimpleNamespace(transcribe=lambda _: text), inputs.append, states.append)
    voice.enabled.set()
    voice.spoken.append((voice.clock(), "Klippy own speech"))
    try:
        voice._transcribe(np.ones(3200, dtype=np.float32), voice.epoch, False, True)
        voice.asr_pool.submit(lambda: None).result(timeout=3)
        assert not inputs and states[0] == "Thinking" and states[-1] == "Speech finished"
    finally:
        voice.close()


def test_printer_preferences_window_flags_reduced_motion_and_cleanup(orb, rig):
    value, data, clock = orb
    value.set_printer("Simulated Mercury")
    value.configure(pinned=True, diameter=256, animations=False)
    assert value.width() == 256 and value.isVisible()
    assert "Simulated Mercury" in value.accessibleDescription()
    flags = value.windowFlags()
    assert flags & Qt.WindowType.WindowStaysOnTopHint and flags & Qt.WindowType.WindowDoesNotAcceptFocus
    assert value.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    assert value.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert value.focusPolicy() == Qt.FocusPolicy.NoFocus and value.windowType() == Qt.WindowType.Tool
    assert not value.moving and value.animation.interval() == 100
    value.configure(animations=True)
    value.motion_reduced = True
    assert not value.moving
    value.configure(enabled=False)
    assert not value.isVisible()
    assert rig[0].get("voice_orb")["diameter"] == 256
    value.shutdown()
    value.refresh()
    assert not value.animation.isActive() and not value.geometry_timer.isActive()
    assert not value.isVisible() and value.source() == {}


def test_tray_monitor_selected_drag_clamped_and_missing_monitor_recovers(orb, monkeypatch):
    value, _, _ = orb
    primary = SimpleNamespace(name=lambda: "primary", geometry=lambda: QRect(0, 0, 1920, 1080),
                              availableGeometry=lambda: QRect(0, 0, 1920, 1032), devicePixelRatio=lambda: 1)
    secondary = SimpleNamespace(name=lambda: "secondary", geometry=lambda: QRect(-1920, 0, 1920, 1080),
                                availableGeometry=lambda: QRect(-1920, 0, 1920, 1032), devicePixelRatio=lambda: 1.5)
    with monkeypatch.context() as m:
        m.setattr(QApplication, "screens", staticmethod(lambda: [primary, secondary]))
        m.setattr(QApplication, "primaryScreen", staticmethod(lambda: primary))
        m.setattr(QApplication, "screenAt", staticmethod(lambda p: secondary if p.x() < 0 else primary))
        m.setattr("klippy.orb.observe_windows", lambda name, b, w, scale: Desktop(b, w, scale))
        value.tray_geometry = lambda: QRect(-20, 1040, 16, 16)
        value.reposition()
        assert value.monitor_name == "secondary" and value.x() < 0
        value.mousePressEvent(SimpleNamespace(button=lambda: Qt.MouseButton.LeftButton,
                                             globalPosition=lambda: QPointF(value.x()+10, value.y()+10)))
        value.mouseMoveEvent(SimpleNamespace(buttons=lambda: Qt.MouseButton.LeftButton,
                                            globalPosition=lambda: QPointF(1900, 1070)))
        assert value.y()+value.height() < 1032  # Clamp even while dragging over the taskbar.
        value.mouseReleaseEvent(object())
        assert value.prefs.position == "custom" and value.prefs.custom_monitor == "primary"
        value.configure(position="custom", custom_monitor="disconnected", custom_position=[99999, 99999])
        assert value.monitor_name == "primary" and value.x()+value.width() < 1920
        value.configure(position="clock", custom_position=None)
        assert value.monitor_name == "secondary"


@pytest.mark.parametrize("scale", [1, 1.25, 1.5, 2])
@pytest.mark.parametrize("edge", ["bottom", "top", "left", "right"])
@pytest.mark.parametrize("auto", [False, True])
def test_multi_dpi_edges_autohide_and_custom_clamping(scale, edge, auto):
    bounds = Rect(-1920, -200, 1920, 1080)
    bars = {"bottom": Rect(-1920, 832, 1920, 48), "top": Rect(-1920, -200, 1920, 48),
            "left": Rect(-1920, -200, 48, 1080), "right": Rect(-48, -200, 48, 1080)}
    desktop = Desktop(bounds, bounds, scale, bars[edge], edge, auto, True)
    area = safe_area(desktop)
    x, y, size = placement(desktop, 192)
    clearance = {"bottom": area.bottom-y-size, "top": y-area.y,
                 "left": x-area.x, "right": area.right-x-size}[edge]
    assert 8 <= clearance*scale <= 12
    for custom in [(-9999, -9999), (9999, 9999)]:
        x, y, size = placement(desktop, 384, custom)
        assert area.x <= x and area.y <= y and x+size <= area.right and y+size <= area.bottom


def test_mixed_dpi_conversion_keeps_monitor_origin_and_fallback_reserves_bar():
    native = Rect(1920, -720, 2560, 1440)
    logical = Rect(1920, -720, 1280, 720)
    result = native_to_logical(Rect(1920, 624, 2560, 96), native, logical, 2)
    assert result == Rect(1920, -48, 1280, 48)
    desktop = Desktop(Rect(0, 0, 1920, 1080), Rect(0, 0, 1920, 1080))
    assert placement(desktop, 192) == (1718, 830, 192)
    tiny = Desktop(Rect(0, 0, 20, 20), Rect(0, 0, 20, 15))
    x, y, size = placement(tiny, 192)
    assert x >= 0 and y >= 0 and x+size <= 20 and y+size <= 15


def test_native_geometry_matches_qt_friendly_monitor_names_without_crossing_monitors():
    logical = Rect(1920, -720, 1280, 720)
    assert same_monitor("Friendly EDID name", logical, "DISPLAY2", Rect(1920, -720, 2560, 1440))
    assert not same_monitor("Friendly EDID name", logical, "DISPLAY1", Rect(0, 0, 1920, 1080))


@pytest.mark.parametrize("invalid", [{"enabled": "yes"}, {"diameter": 0}, {"hide_delay": -1},
                                     {"intensity": float("nan")}, {"custom_position": [100001, 0]}, {"heat": True}])
def test_bad_orb_restore_is_atomic_and_does_not_change_permissions(rig, tmp_path, invalid):
    store = rig[0]
    path = tmp_path / "settings.json"
    store.export(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["preferences"]["voice_orb"] = invalid
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        store.restore(path)
    assert store.printers()[0].approved and store.get("selected") == "sim"
    assert not list(tmp_path.glob("*.before-restore*"))


def test_orb_backup_roundtrip_never_restores_microphone_or_printer_approval(rig, tmp_path):
    store = rig[0]
    settings = preferences({"diameter": 256, "position": "custom", "custom_position": [-10, 30]}).model_dump(mode="json")
    store.set("voice_orb", settings)
    store.set("listening", {"mode": "always"})
    path = tmp_path / "export.json"
    store.export(path)
    store.set("voice_orb", {})
    store.restore(path)
    assert store.get("voice_orb") == settings
    assert store.get("listening") == {"mode": "manual", "enabled": False}
    assert not store.printers()[0].approved and not rig[1].writes


def test_window_integrates_epochs_active_printer_controls_and_cancel(rig, monkeypatch):
    from klippy.app import Window
    app = QApplication.instance() or QApplication([])
    window = Window(rig[0], smoke=True)
    window.timer.stop()
    try:
        assert window.sprite.printer == "Test Printer"
        window.orb_controls["diameter"].setValue(256)
        assert window.sprite.prefs.diameter == 256
        voice = SimpleNamespace(enabled=threading.Event(), capture_ready=threading.Event(), epoch=5,
                                interrupt=lambda: None, close=lambda: None, pending_token=None,
                                say=lambda *args, **kwargs: None)
        window.voice = voice
        voice.enabled.set()
        window.result("voice_state", VoiceState("Listening", 5))
        assert window.sprite.state == "muted"  # Enabled permission alone is insufficient.
        voice.capture_ready.set()
        window.result("voice_state", VoiceState("Thinking", 5))
        window.result("voice_state", VoiceState("Speech finished", 5, object()))
        assert window.sprite.state == "thinking"  # A replaced loop may reuse an epoch number.
        window.result("voice_state", VoiceState("Speech finished", 4))
        assert window.sprite.state == "thinking"
        window.result("voice_wake", 5)
        assert window.sprite.state == "verifying"
        window.cancel()
        assert window.sprite.phase == "idle" and not window.command_busy and not rig[1].writes
        monkeypatch.setattr(window.worker, "submit", lambda name, coroutine: coroutine.close())
        window.submit_turn("status")
        assert window.sprite.state == "thinking"
        window.result("turn", (window.turn, "Simulated response", False))
        assert window.sprite.phase == "thinking"  # Will prepare spoken output.
    finally:
        window.quit()
        window.deleteLater()
        app.processEvents()
