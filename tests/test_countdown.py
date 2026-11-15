import pytest
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from klippy.orb import VoiceOrb
from klippy.session import Session


@pytest.mark.parametrize("timeout", [0, 10, 30, 77])
def test_session_countdown_only_after_completed_response_and_uses_shared_timeout(timeout):
    clock = [100.0]
    s = Session(lambda: clock[0], timeout)
    s.touch()
    assert not s.snapshot()["ready"]
    hold = s.begin()
    clock[0] += 90
    assert s.snapshot()["held"] and not s.snapshot()["ready"]
    s.finish(hold, response=True)
    value = s.snapshot()
    assert value["ready"] == (timeout > 0)
    assert value["remaining"] == timeout
    if timeout:
        clock[0] += timeout / 2
        assert s.snapshot()["fraction"] == 0.5
        hold = s.begin_active()
        assert not s.snapshot()["ready"]
        clock[0] += 90
        s.finish(hold, response=True)
        assert s.snapshot()["remaining"] == timeout
        s.clear("muted")
        assert s.snapshot()["fraction"] == 0 and not s.snapshot()["ready"]


def test_expiry_reason_is_reported_once_and_new_session_has_new_identity():
    clock = [100.0]
    s = Session(lambda: clock[0])
    events = []
    s.on_event = lambda *args: events.append(args)
    s.touch()
    identity = s.session_id
    s.response_complete()
    clock[0] += 31
    assert not s.snapshot()["active"]
    s.snapshot()
    assert events == [(identity, "timeout")]
    s.touch()
    assert s.session_id != identity


def test_session_identity_renews_without_polling_and_observers_never_run_on_touch():
    clock = [100.0]
    session = Session(lambda: clock[0])
    events = []
    session.on_event = lambda *args: events.append(args)
    session.touch()
    old = session.session_id
    clock[0] += 31
    session.touch()
    new = session.session_id
    assert old != new and not events
    session.snapshot()
    assert events == [(old, "timeout")]
    hold = session.begin_active()
    clock[0] += 90
    session.finish(hold, response=True)
    assert session.session_id == new and session.snapshot()["remaining"] == 30


@pytest.mark.parametrize("blocked", ["playing", "busy", "muted", "expired", "held", "disabled", "verifying"])
def test_orb_hides_countdown_at_all_nonlistening_boundaries(rig, blocked):
    app = QApplication.instance() or QApplication([])
    data = {
        "microphone_ready": True,
        "session_active": True,
        "followup_ready": True,
        "followup_fraction": 0.7,
    }
    orb = VoiceOrb(lambda: None, rig[0], QIcon(), source=lambda: data)
    try:
        assert orb.countdown == 0.7
        if blocked == "playing":
            data["playing"] = True
        elif blocked == "busy":
            data["busy"] = True
        elif blocked == "muted":
            data["microphone_ready"] = False
        elif blocked == "expired":
            data.update(session_active=False, followup_ready=False, followup_fraction=0)
        elif blocked == "held":
            data["followup_ready"] = False
        elif blocked == "disabled":
            orb.configure(show_countdown=False)
        else:
            orb.pipeline_event("Checking wake word")
        orb.refresh()
        assert orb.countdown == 0
    finally:
        orb.close()
        orb.deleteLater()
        app.processEvents()


def test_ring_repaints_with_reduced_motion_and_has_real_red_pixels(rig):
    app = QApplication.instance() or QApplication([])
    data = {
        "microphone_ready": True,
        "session_active": True,
        "followup_ready": True,
        "followup_fraction": 1.0,
    }
    orb = VoiceOrb(lambda: None, rig[0], QIcon(), source=lambda: data)
    try:
        orb.motion_reduced = True
        orb.refresh()
        image = orb.grab().toImage()
        reds = sum(
            1
            for x in range(image.width())
            for y in range(image.height())
            if image.pixelColor(x, y).red() > 210 and image.pixelColor(x, y).green() < 100
        )
        assert reds > 50
        data["followup_fraction"] = 0.25
        orb.refresh()
        assert orb.countdown == 0.25
    finally:
        orb.close()
        orb.deleteLater()
        app.processEvents()
