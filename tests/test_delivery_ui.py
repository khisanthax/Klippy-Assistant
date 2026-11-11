import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from klippy.app import Window  # noqa: E402
from klippy.domain import Action, Intent  # noqa: E402


class Voice:
    def __init__(self):
        self.jobs = []

    def say(self, text, **kwargs):
        self.jobs.append(kwargs)

    def interrupt(self):
        pass

    def close(self):
        pass


@pytest.fixture
def window(rig):
    app = QApplication.instance() or QApplication([])
    value = Window(rig[0], smoke=True)
    value.engine = rig[2]
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
    assert window.voice.jobs[-1]["token"] is None
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
