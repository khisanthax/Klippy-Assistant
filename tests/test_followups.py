import asyncio
import threading
import time

import numpy as np
import pytest

from klippy.conversation import Conversation
from klippy.diagnostics import Timings
from klippy.domain import Action, Intent, Printer
from klippy.safety import Rejected
from klippy.voice import VoiceLoop


async def test_one_wake_multiple_commands_expire_after_completed_exchange(rig):
    _, sim, engine, clock = rig
    c = Conversation(engine, clock=lambda: clock[0])
    assert await c.hear("Klippy status", source="voice")
    clock[0] += 29
    assert "Nozzle" in await c.hear("temperatures", source="voice")
    clock[0] += 29
    assert await c.hear("status", source="voice")
    clock[0] += 31
    assert await c.hear("status", source="voice") is None
    assert not sim.writes


async def test_followup_supersedes_slow_llm_without_losing_session(rig):
    _, sim, engine, clock = rig
    entered, release = asyncio.Event(), asyncio.Event()
    class Slow:
        async def interpret(self, *args):
            entered.set()
            await release.wait()
            return Intent(action=Action.HOME, printer_id="sim")
    c = Conversation(engine, Slow(), clock=lambda: clock[0])
    first = asyncio.create_task(c.hear("Klippy something ambiguous", source="voice"))
    await entered.wait()
    clock[0] += 90
    assert await c.hear("status", source="voice")
    release.set()
    assert await first is None
    assert engine.pending is None and not sim.writes


@pytest.mark.parametrize("phrase,expected", [
    ("What's the nozzle temperature?", "Nozzle: 23.0"),
    ("How hot is the bed?", "Bed: 21.0"),
    ("Tell me the temperatures.", "Nozzle: 23.0"),
    ("What's the temperature on Mercury Two?", "Nozzle: 23.0"),
    ("How far along is the SV08?", "63%"),
    ("Is Mercury Two printing?", "standby"),
])
async def test_natural_read_only_queries_bypass_llm(rig, phrase, expected):
    store, sim, engine, _ = rig
    store.save_printer(Printer(id="mercury", name="Mercury Two", url="http://127.0.0.1:7126", approved=True))
    store.save_printer(Printer(id="sv", name="SV08", url="http://127.0.0.1:7127", approved=True))
    class Forbidden:
        async def interpret(self, *args):
            pytest.fail("deterministic query reached LLM")
    assert expected in await Conversation(engine, Forbidden()).hear(phrase)
    assert not sim.writes


async def test_missing_heater_explicitly_unavailable(rig):
    from klippy.domain import Snapshot
    _, _, engine, _ = rig
    class Client:
        async def snapshot(self):
            return Snapshot(connected=True, ready=True)
    engine.clients = lambda p: Client()
    assert "unavailable" in await Conversation(engine).hear("How hot is the bed?")
    assert "Progress unavailable" in await Conversation(engine).hear("status")


async def test_confirmation_clock_starts_only_after_specific_delivery(rig):
    _, sim, engine, clock = rig
    engine.confirmation_seconds = 30
    await engine.propose(Intent(action=Action.HOME, printer_id="sim"), defer_confirmation=True)
    token = engine.pending.token
    clock[0] += 80
    assert not engine.pending.ready and clock[0] < engine.pending.expires
    engine.delivery_finished("stale", True)
    assert not engine.pending.ready
    engine.delivery_finished(token, True)
    assert engine.pending.ready and engine.pending.expires == clock[0] + 30
    clock[0] += 29
    engine.delivery_finished(token, True)  # Cannot extend an already-armed window.
    clock[0] += 2
    with pytest.raises(Rejected, match="expired"):
        await engine.confirm(token)
    assert not sim.writes


@pytest.mark.parametrize("elapsed,success", [(5, False), (181, True)])
async def test_failed_interrupted_or_unbounded_prompt_cannot_confirm(rig, elapsed, success):
    _, sim, engine, clock = rig
    await engine.propose(Intent(action=Action.HOME, printer_id="sim"), defer_confirmation=True)
    token = engine.pending.token
    clock[0] += elapsed
    engine.delivery_finished(token, success)
    assert engine.pending is None
    with pytest.raises(Rejected):
        await engine.confirm(token)
    assert not sim.writes


async def test_delivery_of_old_prompt_never_arms_replacement(rig):
    _, sim, engine, _ = rig
    intent = Intent(action=Action.HOME, printer_id="sim")
    await engine.propose(intent, defer_confirmation=True)
    old = engine.pending.token
    await engine.propose(intent, defer_confirmation=True)
    engine.delivery_finished(old, True)
    assert not engine.pending.ready
    assert not sim.writes


def test_playback_holds_shared_session_and_reports_actual_drain():
    from types import SimpleNamespace

    from klippy.session import Session
    clock = [100.0]
    entered, release = threading.Event(), threading.Event()
    deliveries = []
    class Backend:
        def synthesize(self, text, cancelled=None):
            entered.set()
            release.wait(3)
            return SimpleNamespace(samples=np.ones(160, dtype=np.float32), sample_rate=16000)
    session = Session(clock=lambda: clock[0])
    session.touch()
    voice = VoiceLoop(Backend(), lambda v: None, lambda v: None, session=session,
                      clock=lambda: clock[0], on_delivery=lambda *v: deliveries.append(v))
    worker = threading.Thread(target=voice._speak)
    worker.start()
    try:
        voice.say("test", token="exact")
        assert entered.wait(2)
        clock[0] += 100
        assert session.until > clock[0]
        release.set()
        deadline = time.monotonic() + 3
        while not voice.playback.remaining and time.monotonic() < deadline:
            time.sleep(.01)
        assert not deliveries
        voice._render(160)
        while not deliveries and time.monotonic() < deadline:
            time.sleep(.01)
        assert deliveries == [("exact", True)]
        assert session.until == clock[0] + 30
    finally:
        release.set()
        voice.close()
        worker.join(3)


def test_diagnostics_bounded_and_contains_only_numbers():
    clock = [1.0]
    metrics = Timings(clock=lambda: clock[0])
    for _ in range(40):
        key = metrics.new()
        clock[0] += .2
        metrics.mark("first_audio", key)
    assert len(metrics.snapshot()) == 32
    assert metrics.snapshot()[-1]["milliseconds"] == {"first_audio": 200}


def test_streaming_cache_does_not_reload_or_replay_cancelled_generation():
    from collections import OrderedDict
    from types import SimpleNamespace

    from klippy.voice import SherpaBackend
    backend = SherpaBackend.__new__(SherpaBackend)
    backend.voice_id, backend.vocabulary = 0, set()
    backend.cache, backend.cache_bytes = OrderedDict(), 0
    calls = []
    class TTS:
        sample_rate = 16000
        def generate(self, text, sid, callback):
            calls.append(text)
            samples = np.ones(160, dtype=np.float32)
            callback(samples, .5)
            callback(samples, 1)
            return SimpleNamespace(samples=list(np.r_[samples, samples]), sample_rate=16000)
    backend.tts = TTS()
    chunks = []
    backend.synthesize("Ready.", on_chunk=lambda pcm, rate: chunks.append(len(pcm)))
    assert chunks == [160, 160]  # Audio is delivered before generate returns.
    backend.synthesize("Ready.", on_chunk=lambda pcm, rate: chunks.append(len(pcm)))
    assert len(calls) == 1 and chunks[-1] == 320
    backend.synthesize("Ready.", cancelled=lambda: True, on_chunk=lambda *args: pytest.fail("stale PCM"))
    assert backend.cache_bytes == 320 * 4
