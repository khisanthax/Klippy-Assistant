"""Local full-duplex speech. Audio stays in bounded memory; no printer authority exists here."""
from __future__ import annotations

import queue
import re
import threading
import time
from collections import OrderedDict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from .audio import (
    FRAME,
    RATE,
    AudioDiagnostics,
    AudioLevels,
    EchoFilter,
    Playback,
    default_device_pair,
    synthesis_reserve,
)
from .diagnostics import current, timings
from .models import verify_pack
from .resampling import SpeechResampler
from .session import Session
from .speech_text import normalize_for_speech

WAKE_PREFIX = re.compile(r"^(?:(?:hey|hi)[,\s]+)?(?:klippy|clippy|klippi|clippie|clipy|clip\s+e)\b[\s,.!?]*", re.I)


class VoiceState(str):
    def __new__(cls, text, epoch, owner=None):
        value = super().__new__(cls, text)
        value.epoch = epoch
        value.owner = owner
        return value


@dataclass(frozen=True)
class VoiceInput:
    text: str
    epoch: int
    woke: bool
    confirmation_token: str | None = field(default=None, repr=False)
    trace: int | None = None


class SherpaBackend:
    def __init__(self, root: Path, config, sensitivity=0.22):
        import sherpa_onnx as so
        verify_pack(root)
        self.wake_threshold = sensitivity
        def absolute(values):
            return {key: str(root / value) for key, value in values.items()}
        self.kws = so.KeywordSpotter(**absolute(config["wake"]), keywords_threshold=sensitivity,
                                    keywords_score=2.0, num_threads=1)
        self.reset_wake()
        self.asr = so.OfflineRecognizer.from_whisper(**absolute(config["asr"]), num_threads=2)
        self.tts_kind = config.get("tts_kind", "vits")
        if self.tts_kind == "kokoro":
            model = so.OfflineTtsKokoroModelConfig(**absolute(config["tts"]))
            tts_model = so.OfflineTtsModelConfig(kokoro=model, num_threads=2)
        else:
            model = so.OfflineTtsVitsModelConfig(**absolute(config["tts"]))
            tts_model = so.OfflineTtsModelConfig(vits=model, num_threads=2)
        self.tts = so.OfflineTts(so.OfflineTtsConfig(model=tts_model))
        self.vocabulary = set()
        lexicon = config["tts"].get("lexicon")
        if lexicon:
            with (root / lexicon).open(encoding="utf-8") as stream:
                self.vocabulary = {line.split(" ", 1)[0] for line in stream if line.strip()}
        self.voice_id = config.get("voice_id", 0)
        self.cache = OrderedDict()
        self.cache_bytes = 0

    def reset_wake(self):
        self.stream = self.kws.create_stream()

    def wake(self, samples):
        self.stream.accept_waveform(RATE, samples)
        while self.kws.is_ready(self.stream):
            self.kws.decode_stream(self.stream)
        if self.kws.get_result(self.stream):
            self.kws.reset_stream(self.stream)
            return True
        return False

    def transcribe(self, samples):
        stream = self.asr.create_stream()
        stream.accept_waveform(RATE, samples)
        self.asr.decode_stream(stream)
        return stream.result.text

    def synthesize(self, text, cancelled=None, on_chunk=None, on_progress=None):
        # Only this process's serialized TTS worker uses the bounded PCM cache.
        with timings.span("normalization"):
            normalized = normalize_for_speech(text, self.vocabulary or None)
        key = (self.voice_id, normalized)
        if key in self.cache:
            self.cache.move_to_end(key)
            audio = self.cache[key]
            timings.duration("tts_cache_hit", 0)
            if on_chunk and not (cancelled and cancelled()):
                if on_progress:
                    on_progress(1.0)
                on_chunk(audio.samples, audio.sample_rate)
            return audio
        def callback(samples, progress):
            if cancelled and cancelled():
                return 0
            if on_chunk:
                if on_progress:
                    on_progress(progress)
                on_chunk(samples, self.tts.sample_rate)
            return 1
        with timings.span("tts_generation"):
            audio = self.tts.generate(normalized, sid=self.voice_id, callback=callback)
        audio = SimpleNamespace(samples=np.asarray(audio.samples, dtype=np.float32), sample_rate=audio.sample_rate)
        if not (cancelled and cancelled()) and audio.samples.nbytes <= 8 * 1024 * 1024:
            self.cache[key] = audio
            self.cache_bytes += audio.samples.nbytes
            while self.cache_bytes > 32 * 1024 * 1024 or len(self.cache) > 32:
                _, old = self.cache.popitem(last=False)
                self.cache_bytes -= old.samples.nbytes
        return audio


class VoiceLoop:
    """Duplex device owner, independent DSP/KWS worker, serialized ASR and cancellable TTS.

    While speaking, only a new near-end wake may interrupt. Echo alone cannot open a
    follow-up. After playback/tail, ordinary follow-ups resume for the session timeout.
    All transcription results and speech buffers are bound to an interrupt generation.
    """

    def __init__(self, backend, on_text, on_state, on_wake=None, *, clock=time.monotonic,
                 followup_seconds=30, energy_threshold=0.008, session=None, on_delivery=None):
        self.session = session or Session(clock, followup_seconds)
        self.on_delivery = on_delivery or (lambda token, success: None)
        self.backend, self.on_text, self.on_state = backend, on_text, on_state
        self.state_token = object()
        self.on_wake = on_wake or (lambda epoch: None)
        self.clock, self.followup_seconds, self.energy_threshold = clock, followup_seconds, energy_threshold
        self.enabled = threading.Event()
        self.closed = threading.Event()
        self.speaking = threading.Event()
        self.playback = Playback()
        self.levels = AudioLevels(clock)
        self.capture_ready = threading.Event()
        self.audio_metrics = AudioDiagnostics()
        self.output_latency = 0.0
        self.output_key = None
        self.render_key = (0,0)
        self.audio = queue.Queue(maxsize=100)
        self.speech = queue.Queue(maxsize=4)
        self.overrun = threading.Event()
        self.reset_requested = threading.Event()
        self.threads = []
        self.asr_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="klippy-asr")
        self.asr_slots = threading.BoundedSemaphore(2)
        self.echo = EchoFilter()
        self.preroll = deque(maxlen=300)
        self.frames = []
        self.voiced_frames = 0
        self.last_voice = 0.0
        self.last_output = float("-inf")
        self.had_wake = False
        self.capture_epoch = 0
        self.capture_output_context = False
        self.spoken = deque(maxlen=4)  # Only our own responses; ephemeral echo rejection.
        self.spoken_lock = threading.Lock()
        self.delay_ms = 0
        self.pending_token = None
        self.capture_token = None
        self.capture_hold = None
        self.near_end_until = 0.0
        self.probe_pending = threading.Event()
        self.detected_wakes = queue.Queue(maxsize=2)
        self.last_probe = float("-inf")
        self.last_energy = 0.0
        self.last_device_error = None
        self.output_trace = None
        self.first_render = False
        self.wake_at = None
        self.capture_queue_delay = 0.0
        self.diagnostic_lock = threading.Lock()
        self.wake_counts = dict.fromkeys(("captured_frames", "queue_drops", "device_ready", "discontinuities",
                                         "output_discontinuities", "session_resets",
                                         "frames", "voiced_frames", "candidates", "duplicate_candidates",
                                         "asr_started", "prefix_rejected", "echo_rejected", "verified", "delivered"), 0)

    def count(self, stage):
        with self.diagnostic_lock:
            self.wake_counts[stage] += 1

    def wake_diagnostics(self):
        with self.diagnostic_lock:
            return dict(self.wake_counts)

    def _wake_preroll(self):
        # Discard a preceding sentence separated by >=300 ms silence. Keep 100 ms
        # context before the current phrase, including the complete wake prefix.
        frames = list(self.preroll)
        silent, start = 0, 0
        for i, frame in enumerate(frames):
            if float(np.sqrt(np.mean(frame * frame))) < self.energy_threshold:
                silent += 1
            else:
                if silent >= 30:
                    start = max(0, i - 10)
                silent = 0
        return frames[start:]

    @property
    def listen_until(self):
        return self.session.until

    @listen_until.setter
    def listen_until(self, value):
        self.session.deadline = value

    @property
    def epoch(self):
        return self.playback.generation

    def start(self):
        for name, target in [("devices", self._devices), ("dsp", self._process), ("tts", self._speak)]:
            thread = threading.Thread(target=target, name="klippy-" + name, daemon=True)
            self.threads.append(thread)
            thread.start()

    def report_state(self, text, epoch=None):
        self.on_state(VoiceState(text, self.epoch if epoch is None else epoch, self.state_token))

    def interrupt(self):
        epoch = self.playback.interrupt()
        self.levels.clear()
        self.speaking.clear()
        return epoch

    def reset_session(self):
        self.count("session_resets")
        self.interrupt()
        self.session.clear()
        self.reset_requested.set()

    def close(self):
        self.closed.set()
        self.enabled.clear()
        self.capture_ready.clear()
        self.interrupt()
        self.session.clear()
        while not self.speech.empty():
            try:
                job = self.speech.get_nowait()
                self.on_delivery(job[2], False)
            except queue.Empty:
                break
        for thread in self.threads:
            thread.join(timeout=4)
        self.asr_pool.shutdown(wait=True, cancel_futures=True)

    def say(self, text, token=None, trace=None):
        if self.closed.is_set():
            return
        hold = self.session.begin_active()
        job = (self.epoch, text[:600], token, trace, hold, self.clock())
        try:
            self.speech.put_nowait(job)
        except queue.Full:
            try:
                old = self.speech.get_nowait()
                self.session.finish(old[4])
                self.on_delivery(old[2], False)
            except queue.Empty:
                pass
            self.speech.put_nowait(job)

    def _speak(self):
        while not self.closed.is_set():
            try:
                epoch, text, token, trace, hold, queued = self.speech.get(timeout=0.2)
            except queue.Empty:
                continue
            context = current.set(trace)
            success = False
            try:
                if epoch != self.epoch:
                    continue
                timings.duration("tts_queue", self.clock() - queued)
                self.speaking.set()
                stream = self.playback.begin(epoch)
                if stream is None:
                    raise RuntimeError('Previous speech buffer did not drain')
                self.output_key = (epoch,stream)
                self.report_state("Speaking", epoch)  # Existing event means preparation; rendered PCM drives the orb.
                self.output_trace, self.first_render = trace, False
                with self.spoken_lock:
                    self.spoken.append((self.clock(), text))
                converter = None
                progress = 0.0
                first_chunk = True
                synth_began = time.monotonic()
                def observed_progress(value):
                    nonlocal progress
                    if np.isfinite(value) and 0 < value <= 1:
                        progress = float(value)
                def chunk(samples, rate):
                    nonlocal converter, first_chunk
                    if epoch == self.epoch and not self.closed.is_set():
                        pcm = np.asarray(samples,dtype=np.float32)
                        if pcm.size and np.isfinite(pcm).all():
                            self.audio_metrics.peak('source_peak',float(np.max(np.abs(pcm))))
                        if converter is None:
                            converter = SpeechResampler(rate)
                        elif rate != converter.source:
                            raise ValueError('TTS changed sample rate mid-utterance')
                        # SDK progress describes completed sentence groups. Under slow
                        # generation, reserve bounded time for future chunks; never sleep
                        # or resample inside capture/render callbacks.
                        if first_chunk and 0 < progress < 1 and len(pcm):
                            now = time.monotonic()
                            duration = len(pcm)/rate
                            reserve=synthesis_reserve(now-synth_began,duration,progress)
                            self.playback.defer_start(epoch,stream,now+min(2.0,reserve),complete_first=reserve>2.0)
                        first_chunk = False
                        timings.mark("tts_first_pcm")
                        self.playback.enqueue(converter.push(pcm),epoch,stream=stream)
                def cancelled():
                    return epoch != self.epoch or self.closed.is_set()
                if isinstance(self.backend, SherpaBackend):
                    audio = self.backend.synthesize(text, cancelled=cancelled, on_chunk=chunk,
                                                    on_progress=observed_progress)
                    if converter is None:
                        chunk(audio.samples,audio.sample_rate)
                    self.playback.enqueue(converter.finish(),epoch,stream=stream,final=True)
                else:
                    audio = self.backend.synthesize(text, cancelled=cancelled)
                    pcm = np.asarray(audio.samples,dtype=np.float32)
                    if pcm.size and np.isfinite(pcm).all():
                        self.audio_metrics.peak('source_peak',float(np.max(np.abs(pcm))))
                    converted = SpeechResampler(audio.sample_rate).push(pcm,final=True)
                    self.playback.enqueue(converted,epoch,stream=stream,final=True)
                deadline = time.monotonic() + 90
                while self.playback.remaining and not cancelled():
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Playback did not drain")
                    self.closed.wait(0.02)
                # PortAudio has consumed PCM, but the DAC and echo tail must finish too.
                tail_end = time.monotonic() + max(.65, self.delay_ms / 1000 + .1, self.output_latency+.1)
                while time.monotonic() < tail_end and not cancelled():
                    self.closed.wait(.02)
                success = not cancelled() and self.playback.receipt(epoch,stream)
                timings.mark("playback_complete")
            except Exception:
                if epoch == self.epoch:
                    self.interrupt()
                    self.report_state("Speaker or speech model unavailable; text remains accessible")
            finally:
                if epoch == self.epoch:
                    self.speaking.clear()
                self.session.finish(hold, refresh=success or (epoch == self.epoch and not self.closed.is_set()))
                self.on_delivery(token, success)
                self.report_state("Speech finished" if success else "Speech interrupted or failed", epoch)
                current.reset(context)

    def _render(self, frames):
        output, consumed, generation, stream = self.playback.render_packet(frames)
        self.render_key = (generation,stream)
        peak = float(np.max(np.abs(output),initial=0))
        self.audio_metrics.peak('preclip_peak',peak)
        if peak>1:
            self.playback.mark_fault(generation,stream,'clipped_samples',int(np.count_nonzero(np.abs(output)>1)))
            np.clip(output,-1,1,out=output)  # AEC receives precisely these DAC-bound samples.
        self.audio_metrics.peak('render_peak',min(1.0,peak))
        self.levels.publish("playback", float(np.sqrt(np.mean(output*output))), rendered=consumed>0)
        if np.any(output) and not self.first_render and (self.output_key is None or self.output_key==self.render_key):
            self.first_render = True
            timings.mark("first_audio_render", self.output_trace)
            timings.mark("first_audible_estimate", self.output_trace,
                         at=self.clock() + self.delay_ms / 1000)
        return output

    def _callback(self, indata, outdata, frames, timing, status):
        began = time.perf_counter()
        try:
            self._capture_callback(indata,outdata,frames,timing,status)
        finally:
            self.audio_metrics.callback(began,time.perf_counter()-began)

    def _capture_callback(self, indata, outdata, frames, timing, status):
        output = self._render(frames)
        outdata[:, 0] = output
        if not self.enabled.is_set():
            return
        self.count("captured_frames")
        try:
            fault = self.callback_fault(status)
            if fault == 2:
                self.record_output_status(status)
            delay = max(0, min(500, round((timing.outputBufferDacTime - timing.inputBufferAdcTime) * 1000)))
            self.audio.put_nowait((indata[:, 0].copy(), output, self.clock(),
                                   self.speaking.is_set(), delay, fault))
        except queue.Full:
            self.count("queue_drops")
            self.overrun.set()

    @staticmethod
    def callback_fault(status):
        if not status:
            return 0
        if not hasattr(status, "input_overflow"):
            return 1  # Unknown status must not authorize continuous capture.
        if status.input_overflow or status.input_underflow or status.priming_output:
            return 1
        return 2 if status.output_underflow or status.output_overflow else 1

    def _output_callback(self, outdata, frames, timing, status):
        began = time.perf_counter()
        try:
            output = self._render(frames)
            if status:
                self.record_output_status(status)
            outdata[:, 0] = output
            if np.any(output):
                self.last_output = self.clock()
        finally:
            self.audio_metrics.callback(began,time.perf_counter()-began)

    def playback_diagnostics(self):
        return {**self.playback.diagnostics(), **self.audio_metrics.snapshot()}

    def record_output_status(self, status):
        kind = ('device_underflows' if getattr(status,'output_underflow',False) else
                'device_overflows' if getattr(status,'output_overflow',False) else 'device_status_events')
        self.playback.mark_fault(*self.render_key,kind)

    def _clear_capture(self):
        self.session.finish(self.capture_hold, refresh=False)
        self.capture_hold = None
        self.frames.clear()
        self.voiced_frames = 0
        self.had_wake = False
        self.capture_output_context = False

    def _reset_dsp(self):
        self._clear_capture()
        self.session.clear()
        self.preroll.clear()
        self.near_end_until = 0.0
        self.backend.reset_wake()
        self.echo = EchoFilter(self.delay_ms)
        while not self.audio.empty():
            try:
                self.audio.get_nowait()
            except queue.Empty:
                break

    def process_frame(self, near, far, now, *, output_active=False):
        """Same path for live capture and deterministic, device-free integration tests."""
        input_epoch = self.epoch
        cleaned = self.echo.process(near, far)
        self.preroll.append(cleaned)
        if np.any(far):
            self.last_output = now
        output_context = output_active or now - self.last_output < 0.65
        energy = float(np.sqrt(np.mean(cleaned * cleaned)))
        self.levels.publish("microphone", energy)
        self.last_energy = energy
        voiced = energy >= self.energy_threshold
        self.count("frames")
        if voiced:
            self.count("voiced_frames")
        if output_context and voiced and len(self.echo.near) >= 10:
            # Latch double-talk evidence across syllable gaps. Resetting KWS on every
            # echo-dominated gap erases short wake words while the assistant speaks.
            correlation = self.echo.reference_correlation()
            if correlation < .65:
                self.near_end_until = now + .8
        near_end = not output_context or now < self.near_end_until
        if voiced:
            self.last_voice = now
        wake = self.backend.wake(cleaned)
        accepted_probe = False
        try:
            probe_epoch = self.detected_wakes.get_nowait()
            accepted_probe = probe_epoch == self.epoch
        except queue.Empty:
            pass
        if accepted_probe:
            wake, near_end = True, True
        if wake:
            self.count("candidates")
        if wake and self.frames and self.had_wake and self.capture_epoch == self.epoch:
            # A second KWS hit in one utterance must not erase its first words or
            # supersede the captured confirmation token. Final ASR still verifies it.
            self.count("duplicate_candidates")
            wake = False
        if self.echo.echo_only and not near_end:
            self._clear_capture()
            return
        if wake and near_end:
            self.wake_at = now
            epoch = self.epoch if accepted_probe else self.interrupt()
            if not accepted_probe:
                self.on_wake(epoch)
            self.report_state("Checking wake word", epoch)
            self._clear_capture()
            self.capture_hold = self.session.begin_active()
            self.frames = self._wake_preroll()
            self.voiced_frames = sum(float(np.sqrt(np.mean(f * f))) >= self.energy_threshold for f in self.frames)
            self.had_wake = True
            self.capture_epoch = epoch
            self.capture_token = self.pending_token
            self.capture_output_context = output_context
        elif not self.frames:
            if output_active and near_end and voiced and not self.probe_pending.is_set() and now - self.last_probe >= .45:
                # AEC-conditioned KWS can miss a very short name during double-talk.
                # The already-bundled local ASR verifies that exact wake prefix as a
                # second path. It cannot forward a command or confirm an action.
                if len(self.preroll) >= 40:
                    self.last_probe = now
                    self._probe_wake(np.concatenate(list(self.preroll)[-160:]), self.epoch)
            if output_active or now >= self.listen_until or not voiced:
                return
            self.capture_hold = self.session.begin_active()
            if self.capture_hold is None or input_epoch != self.epoch:
                self._clear_capture()
                return
            self.frames = list(self.preroll)[-20:]
            self.voiced_frames = 1
            self.capture_epoch = input_epoch
            self.capture_token = self.pending_token
            self.capture_output_context = output_context
        else:
            if output_active and not self.had_wake:
                self._clear_capture()
                return
            self.frames.append(cleaned)
            self.voiced_frames += int(voiced)
            self.capture_output_context |= output_context
        if self.frames and (now - self.last_voice >= 0.6 or len(self.frames) >= 1500):
            if self.voiced_frames >= 8:
                self._transcribe(np.concatenate(self.frames), self.capture_epoch,
                                 self.had_wake, self.capture_output_context, self.capture_token)
            self._clear_capture()
            self.preroll.clear()

    def _is_own_text(self, text):
        normalized = re.sub(r"[^a-z0-9 ]", "", normalize_for_speech(text))
        with self.spoken_lock:
            own = [normalize_for_speech(t) for at, t in self.spoken if self.clock() - at < 60]
        return bool(normalized) and any(normalized in t or SequenceMatcher(None, normalized, t).ratio() >= .8 for t in own)

    def _probe_wake(self, samples, epoch):
        if not self.asr_slots.acquire(blocking=False):
            return
        self.probe_pending.set()
        def run():
            try:
                if epoch != self.epoch or not self.enabled.is_set() or self.closed.is_set():
                    return
                text = self.backend.transcribe(samples).strip()
                if (epoch == self.epoch and self.enabled.is_set() and not self.closed.is_set()
                        and WAKE_PREFIX.match(text) and not self._is_own_text(text)):
                    new_epoch = self.interrupt()
                    self.on_wake(new_epoch)
                    try:
                        self.detected_wakes.put_nowait(new_epoch)
                    except queue.Full:
                        pass
            except Exception:
                self.report_state("Wake verification unavailable; keyword detector remains active", epoch)
            finally:
                self.probe_pending.clear()
                self.asr_slots.release()
        self.asr_pool.submit(run)

    def _transcribe(self, samples, epoch, woke, output_context, confirmation_token=None):
        if not self.asr_slots.acquire(blocking=False):
            self.reset_session()
            self.report_state("Speech queue full; please wake Klippy and repeat")
            return
        trace = timings.new(self.last_voice)
        timings.mark("vad_end", trace)
        timings.duration("audio_queue", self.capture_queue_delay, trace)
        if woke and self.wake_at is not None:
            timings.mark("wake", trace, at=self.wake_at)
        queued = self.clock()
        hold = self.session.begin() if not woke or self.clock() < self.session.until else None
        def run():
            accepted = False
            context = current.set(trace)
            try:
                if epoch != self.epoch or not self.enabled.is_set() or self.closed.is_set():
                    return
                timings.duration("asr_queue", self.clock() - queued)
                self.report_state("Thinking", epoch)
                self.count("asr_started")
                with timings.span("asr"):
                    text = self.backend.transcribe(samples).strip()
                timings.mark("asr_complete")
                if epoch != self.epoch or not self.enabled.is_set() or self.closed.is_set() or not text:
                    return
                match = WAKE_PREFIX.match(text)
                if woke and match is None:
                    self.count("prefix_rejected")
                    self.report_state("Wake transcript unclear; please repeat Klippy and the request", epoch)
                    return
                if output_context:
                    if self._is_own_text(text):
                        self.count("echo_rejected")
                        return
                if match:
                    text = "Klippy " + text[match.end():]
                with self.playback.lock:
                    if epoch != self.playback.generation or not self.enabled.is_set() or self.closed.is_set():
                        return
                    self.session.touch()
                    accepted = True
                if woke:
                    self.count("verified")
                    self.report_state("Listening", epoch)
                self.count("delivered")
                self.on_text(VoiceInput(text, epoch, woke, confirmation_token, trace))
            except Exception:
                self.report_state("Speech recognition unavailable; no request sent", epoch)
            finally:
                if hold is not None:
                    self.session.finish(hold, refresh=accepted and epoch == self.epoch)
                if not accepted and epoch == self.epoch:
                    self.report_state("Speech finished", epoch)
                current.reset(context)
                self.asr_slots.release()
        self.asr_pool.submit(run)

    def _process(self):
        while not self.closed.is_set():
            if self.overrun.is_set() or self.reset_requested.is_set():
                self.overrun.clear()
                self.reset_requested.clear()
                self._reset_dsp()
            try:
                near, far, now, active, delay, discontinuity = self.audio.get(timeout=0.2)
            except queue.Empty:
                continue
            if not self.enabled.is_set():
                continue
            if discontinuity == 2 and len(near) == FRAME:
                # Output loss invalidates AEC reference and prompt delivery, not
                # continuous microphone permission or the shared conversation clock.
                self._clear_capture()
                self.preroll.clear()
                self.echo = EchoFilter(self.delay_ms)
                self.count("output_discontinuities")
                continue
            if discontinuity or len(near) != FRAME:
                self.count("discontinuities")
                self.reset_session()
                self.report_state("Audio discontinuity; please wake Klippy and repeat")
                continue
            try:
                if abs(delay - self.delay_ms) > 20:
                    self.delay_ms = delay
                    self.echo.processor.stream_delay_ms = delay
                self.capture_queue_delay = max(0, self.clock() - now)
                self.process_frame(near, far, now, output_active=active)
            except Exception:
                self.reset_session()
                self.report_state("Audio processing unavailable; no request sent")

    def _devices(self):
        import sounddevice as sd

        from .windows_audio import default_endpoint_ids
        last_ids = None
        while not self.closed.is_set():
            if not self.enabled.is_set() and not self.speaking.is_set() and not self.playback.remaining:
                self.closed.wait(0.05)
                continue
            if self.closed.is_set():
                break
            try:
                capturing = self.enabled.is_set()
                ids = default_endpoint_ids(require_input=capturing)
                if ids != last_ids:
                    # This class is the sole PortAudio owner. Refresh after closing streams.
                    sd._terminate()
                    sd._initialize()
                    last_ids = ids
                pair = default_device_pair(sd)
                output_info = sd.query_devices(pair[1])
                extra = sd.WasapiSettings(auto_convert=True) if sd.query_hostapis(output_info["hostapi"])["name"] == "Windows WASAPI" else None
                default_latency = getattr(getattr(sd,'default',None),'latency',('low','low'))
                input_latency = default_latency if isinstance(default_latency,str) else default_latency[0]
                output_latency = max(.08,output_info.get('default_high_output_latency',0))
                stream = (sd.Stream(device=pair, samplerate=RATE, channels=1, dtype="float32", blocksize=FRAME,
                                    extra_settings=extra, latency=(input_latency,output_latency), callback=self._callback) if capturing else
                          sd.OutputStream(device=pair[1], samplerate=RATE, channels=1, dtype="float32", blocksize=FRAME,
                                          extra_settings=extra, latency=output_latency, callback=self._output_callback))
                with stream:
                    latency = getattr(stream,'latency',(0,0) if capturing else 0)
                    self.audio_metrics.device(latency)
                    self.output_latency = latency[1] if isinstance(latency,tuple) else latency
                    if capturing:
                        self.capture_ready.set()
                        self.count("device_ready")
                        self.report_state("Microphone ready")
                    while not self.closed.wait(0.25):
                        if self.enabled.is_set() != capturing:
                            break
                        if not capturing and not self.speaking.is_set() and not self.playback.remaining:
                            break
                        if default_endpoint_ids(require_input=capturing) != ids:
                            self.report_state("Default audio device changed; reconnecting")
                            break
                self.capture_ready.clear()
                self.reset_session()
            except Exception as exc:
                self.capture_ready.clear()
                self.last_device_error = type(exc).__name__ + ": " + str(exc)
                self.reset_session()
                self.report_state("Microphone or speaker unavailable; retrying safely")
                last_ids = None
                self.closed.wait(2)
