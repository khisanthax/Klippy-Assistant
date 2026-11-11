import threading
from types import SimpleNamespace

import numpy as np
import pytest

from klippy.audio import FRAME, RATE, EchoFilter, Playback, resample
from klippy.speech_text import cmu_to_ipa, normalize_for_speech
from klippy.voice import VoiceLoop


class Backend:
    def __init__(self):
        self.trigger = False
        self.text = "Klippy status"
        self.entered = threading.Event()
        self.release = threading.Event()
        self.block_asr = False
        self.asr_calls = 0

    def wake(self, samples):
        result, self.trigger = self.trigger, False
        return result

    def reset_wake(self):
        pass

    def transcribe(self, samples):
        self.asr_calls += 1
        self.entered.set()
        if self.block_asr:
            self.release.wait(3)
        return self.text

    def synthesize(self, text, cancelled=None):
        return SimpleNamespace(samples=np.ones(3200, dtype=np.float32) * .1, sample_rate=RATE)


@pytest.fixture
def loop():
    backend = Backend()
    values, states, wakes = [], [], []
    clock = [0.0]
    voice = VoiceLoop(backend, values.append, states.append, wakes.append, clock=lambda: clock[0])
    voice.enabled.set()
    yield voice, backend, values, states, wakes, clock
    backend.release.set()
    voice.close()


def feed(voice, clock, count, *, signal=True, output=False):
    rng = np.random.default_rng(21)
    for _ in range(count):
        clock[0] += .01
        near = rng.normal(0, .05, FRAME).astype(np.float32) if signal else np.zeros(FRAME, dtype=np.float32)
        voice.process_frame(near, np.zeros(FRAME, dtype=np.float32), clock[0], output_active=output)


def drain(voice):
    voice.asr_pool.submit(lambda: None).result(timeout=4)


def test_nonwake_speech_and_silence_never_transcribed(loop):
    voice, backend, values, _, _, clock = loop
    feed(voice, clock, 100)
    feed(voice, clock, 100, signal=False)
    drain(voice)
    assert not values and backend.asr_calls == 0


def test_wake_preserves_preroll_and_transcribes_request(loop):
    voice, backend, values, _, wakes, clock = loop
    feed(voice, clock, 50)
    backend.trigger = True
    feed(voice, clock, 40)
    feed(voice, clock, 100, signal=False)
    drain(voice)
    assert len(wakes) == 1 and values[0].text == "Klippy status"
    assert values[0].woke


def test_barge_in_flushes_playback_before_asr(loop):
    voice, backend, _, _, wakes, clock = loop
    voice.playback.enqueue(np.ones(16000, dtype=np.float32), voice.epoch)
    feed(voice, clock, 20, output=True)
    backend.trigger = True
    feed(voice, clock, 1, output=True)
    assert wakes and voice.playback.remaining == 0
    assert not voice.playback.render().any()
    assert backend.asr_calls == 0


def test_playback_nearend_without_wake_cannot_forward_confirmation(loop):
    voice, backend, values, _, wakes, clock = loop
    voice.listen_until = 30
    voice.playback.enqueue(np.ones(32000, dtype=np.float32), voice.epoch)
    backend.text = "confirm"
    feed(voice, clock, 100, output=True)
    feed(voice, clock, 100, signal=False, output=True)
    drain(voice)
    assert not values and not wakes and backend.asr_calls > 0
    assert voice.playback.remaining == 32000


def test_stale_asr_is_discarded_after_interruption(loop):
    voice, backend, values, _, _, _ = loop
    backend.block_asr = True
    voice._transcribe(np.ones(3200, dtype=np.float32), voice.epoch, True, False)
    assert backend.entered.wait(2)
    voice.interrupt()
    backend.release.set()
    drain(voice)
    assert not values


def test_muting_before_asr_completion_discards_result(loop):
    voice, backend, values, _, _, _ = loop
    backend.block_asr = True
    voice._transcribe(np.ones(3200, dtype=np.float32), voice.epoch, True, False)
    assert backend.entered.wait(2)
    voice.enabled.clear()
    backend.release.set()
    drain(voice)
    assert not values


def test_own_transcript_echo_never_becomes_request(loop):
    voice, backend, values, _, _, clock = loop
    backend.text = "Klippy home the printer"
    voice.spoken.append((clock[0], "Klippy home the printer"))
    voice._transcribe(np.ones(3200, dtype=np.float32), voice.epoch, True, True)
    drain(voice)
    assert not values


def test_confirmation_keeps_token_from_capture_not_current_context(loop):
    voice, backend, values, _, _, _ = loop
    backend.text = "confirm"
    voice.pending_token = "new-context"
    voice._transcribe(np.ones(3200, dtype=np.float32), voice.epoch, False, False, "captured-context")
    drain(voice)
    assert values[0].confirmation_token == "captured-context"


def test_old_synthesis_cannot_enqueue_after_interrupt():
    playback = Playback()
    epoch = playback.generation
    playback.interrupt()
    assert not playback.enqueue(np.ones(1600, dtype=np.float32), epoch)
    assert not playback.render().any()


def test_playback_packet_boundaries_and_flush():
    playback = Playback()
    playback.enqueue(np.arange(200, dtype=np.float32), playback.generation)
    assert np.array_equal(playback.render(160), np.arange(160, dtype=np.float32))
    assert np.array_equal(playback.render(80), np.r_[np.arange(160, 200), np.zeros(40)])
    assert playback.remaining == 0


def test_webrtc_cancels_delayed_scaled_echo_without_devices():
    rng = np.random.default_rng(8)
    far = rng.normal(0, .08, RATE * 3).astype(np.float32)
    near = .5 * np.roll(far, 800)
    near[:800] = 0
    echo = EchoFilter(50)
    output = np.concatenate([echo.process(near[i:i + FRAME], far[i:i + FRAME])
                             for i in range(0, len(far), FRAME)])
    assert np.mean(output[-RATE:] ** 2) / np.mean(near[-RATE:] ** 2) < .03
    assert echo.reference_correlation() > .9


def test_linear_path_preserves_nearend_during_doubletalk():
    rng = np.random.default_rng(32)
    far = rng.normal(0, .08, RATE * 3).astype(np.float32)
    near = .6 * np.roll(far, 800) + .1 * np.roll(far, 1120)
    near[:1120] = 0
    user = np.zeros_like(near)
    user[RATE * 2:] = rng.normal(0, .06, RATE).astype(np.float32)
    near += user
    echo = EchoFilter(50)
    output = np.concatenate([echo.process(near[i:i + FRAME], far[i:i + FRAME])
                             for i in range(0, len(far), FRAME)])
    assert echo.linear_kernel is not None
    assert np.corrcoef(output[-RATE:], user[-RATE:])[0, 1] > .95
    assert np.mean(output[-RATE:] ** 2) > .8 * np.mean(user[-RATE:] ** 2)


def test_resampling_duration_and_numbers_acronyms():
    assert len(resample(np.zeros(24000, dtype=np.float32), 24000)) == RATE
    text = normalize_for_speech("SV08: nozzle 235.5 degrees; 63%")
    assert "s v zero eight" in text and "two hundred thirty five point five" in text
    assert "sixty three percent" in text
    assert cmu_to_ipa(["K", "L", "IH1", "P", "IY0"]) == list("klˈɪpi")


def test_wake_without_validated_transcript_rejects_clip_per(loop):
    voice, backend, values, _, _, _ = loop
    backend.text = "Klipper home"
    voice._transcribe(np.ones(3200, dtype=np.float32), voice.epoch, True, False)
    drain(voice)
    assert not values
