"""Testable duplex audio primitives. No model, network, device, or printer control here."""
import threading
import time
from collections import deque

import numpy as np

RATE = 16000
FRAME = 160  # WebRTC AEC uses 10 ms frames.


class AudioLevels:
    """Best-effort numeric telemetry. Never blocks audio or retains PCM/transcripts."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.Lock()
        self.values = {"microphone": [0.0, float("-inf")], "playback": [0.0, float("-inf")]}
        self.playing_until = float("-inf")

    def publish(self, source, level, *, rendered=False):
        if not self.lock.acquire(blocking=False):
            return  # Drop visualization data, never delay a voice frame.
        try:
            now = self.clock()
            row = self.values[source]
            row[0] = max(row[0] if now-row[1] < .2 else 0, min(1.0, max(0.0, float(level))))
            row[1] = now
            if rendered:
                self.playing_until = now + .15
        finally:
            self.lock.release()

    def snapshot(self):
        with self.lock:
            now = self.clock()
            values = {key: row[0] if now-row[1] < .2 else 0.0 for key, row in self.values.items()}
            for row in self.values.values():
                row[0] = 0.0
            return {**values, "playing": now < self.playing_until}

    def clear(self):
        with self.lock:
            for row in self.values.values():
                row[:] = [0.0, float("-inf")]
            self.playing_until = float("-inf")


def resample(samples, source_rate, target_rate=RATE):
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    if source_rate == target_rate or not len(samples):
        return samples.copy()
    length = round(len(samples) * target_rate / source_rate)
    return np.interp(np.arange(length) * source_rate / target_rate,
                     np.arange(len(samples)), samples).astype(np.float32)


class Playback:
    """Generation-bound PCM buffer. Interrupting flushes the next render frame immediately."""

    def __init__(self, clock=time.monotonic):
        self.lock = threading.Lock()
        self.clock = clock
        self.generation = 0
        self.blocks = deque()
        self.offset = 0
        self.remaining = 0
        self.stream_token = 0
        self.producing = self.started = self.faulted = False
        self.starving = False
        self.audible_samples = self.prefill = 0
        self.not_before = 0.0
        self.complete_first = False
        self.stats = dict.fromkeys(('queue_underruns','missing_samples','device_underflows','device_overflows','device_status_events',
                                   'clipped_samples','invalid_pcm','prefill_frames','complete_pcm_fallbacks'),0)

    def begin(self, generation, prefill=RATE*120//1000):
        with self.lock:
            if generation != self.generation or self.remaining:
                return None
            self.stream_token += 1
            self.producing, self.started, self.faulted = True, False, False
            self.starving = False
            self.audible_samples = 0
            self.prefill, self.not_before = prefill, 0.0
            self.complete_first = False
            return self.stream_token

    def buffer_first_chunk(self, generation, stream, elapsed, seconds, progress):
        if not (0 < progress < 1 and elapsed >= 0 and seconds > 0):
            return
        # If the producer already trails playback, one chunk cannot predict how
        # long the remaining sentences take. EOF supplies the delivery boundary.
        complete_first = elapsed >= seconds
        delay = max(0.0, .12 - (seconds - elapsed) * (1 / progress - 1)) if not complete_first else 0.0
        self.defer_start(generation, stream, self.clock() + delay, complete_first=complete_first)

    def defer_start(self, generation, stream, when, *, complete_first=False):
        with self.lock:
            if (generation,stream) == (self.generation,self.stream_token) and not self.started:
                self.not_before = when
                self.complete_first = complete_first
                self.stats['complete_pcm_fallbacks'] += int(complete_first)

    def receipt(self, generation, stream):
        with self.lock:
            return ((generation,stream) == (self.generation,self.stream_token) and
                    not self.producing and not self.remaining and not self.faulted and self.audible_samples>0)

    def mark_fault(self, generation, stream, kind, count=1):
        with self.lock:
            self.stats[kind] += count
            if (generation,stream) == (self.generation,self.stream_token) and self.audible_samples:
                self.faulted = True

    def diagnostics(self):
        with self.lock:
            return dict(self.stats)

    def interrupt(self):
        with self.lock:
            self.generation += 1
            self.blocks.clear()
            self.offset = self.remaining = 0
            self.producing = self.started = self.faulted = False
            self.starving = False
            self.audible_samples = 0
            self.not_before = 0.0
            self.complete_first = False
            return self.generation

    def enqueue(self, samples, generation, *, stream=None, final=False):
        samples = np.asarray(samples, dtype=np.float32).reshape(-1)
        if not np.isfinite(samples).all():
            with self.lock:
                self.stats['invalid_pcm'] += 1
            raise ValueError('Nonfinite TTS PCM')
        samples = samples.copy()
        with self.lock:
            if generation != self.generation or (stream is not None and stream != self.stream_token):
                return False
            if self.remaining + len(samples) > RATE * 60:
                raise ValueError("Speech playback buffer exceeded its limit")
            if len(samples):
                self.blocks.append(samples)
            self.remaining += len(samples)
            if final:
                self.producing = False
            return True

    def render(self, size=FRAME):
        return self.render_packet(size)[0]

    def render_packet(self, size=FRAME):
        output = np.zeros(size, dtype=np.float32)
        with self.lock:
            if not self.started and ((self.complete_first and self.producing) or
                    (not self.complete_first and self.clock()<self.not_before) or
                    (self.producing and self.remaining<self.prefill)):
                self.stats['prefill_frames'] += size
                if self.starving and self.producing:
                    self.stats['missing_samples'] += size
                return output, 0, self.generation, self.stream_token
            if self.remaining:
                self.started = True
            at = 0
            while self.blocks and at < size:
                block = self.blocks[0]
                count = min(size - at, len(block) - self.offset)
                output[at:at + count] = block[self.offset:self.offset + count]
                self.offset += count
                self.remaining -= count
                at += count
                if self.offset == len(block):
                    self.blocks.popleft()
                    self.offset = 0
            self.audible_samples += int(np.count_nonzero(np.abs(output)>1e-5))
            if self.producing and (self.started or self.starving) and at<size:
                if not self.starving:
                    self.stats['queue_underruns'] += 1
                self.stats['missing_samples'] += size-at
                self.faulted = True
                self.started = False
                self.starving = True
            elif at:
                self.starving = False
            return output, at, self.generation, self.stream_token


class AudioDiagnostics:
    """Numeric capture/playback observations; producer never waits for the UI reader."""
    def __init__(self):
        self.lock = threading.Lock()
        self.last_callback = None
        self.values = {'callbacks':0,'max_callback_gap_ms':0.0,'max_callback_work_ms':0.0,
                       'input_peak':0.0,'input_rms':0.0,'input_zero_frames':0,'dsp_max_work_ms':0.0,'dsp_queue_delay_ms':0.0,
                       'source_peak':0.0,'preclip_peak':0.0,'render_peak':0.0,'input_latency_ms':0.0,'output_latency_ms':0.0}

    def callback(self, began, elapsed):
        if not self.lock.acquire(False):
            return
        try:
            if self.last_callback is not None:
                self.values['max_callback_gap_ms'] = max(self.values['max_callback_gap_ms'],
                                                        (began-self.last_callback)*1000)
            self.last_callback = began
            self.values['callbacks'] += 1
            self.values['max_callback_work_ms'] = max(self.values['max_callback_work_ms'],elapsed*1000)
        finally:
            self.lock.release()

    def capture(self, samples):
        # Numeric levels only; never retain samples or wait on a UI/diagnostic reader.
        peak = float(np.max(np.abs(samples), initial=0))
        rms = float(np.sqrt(np.mean(samples * samples))) if len(samples) else 0.0
        if np.isfinite(peak) and np.isfinite(rms) and self.lock.acquire(False):
            try:
                self.values['input_peak'] = max(self.values['input_peak'], peak)
                self.values['input_rms'] = rms
                self.values['input_zero_frames'] += int(peak <= 1e-7)
            finally:
                self.lock.release()

    def processing(self, elapsed, queue_delay):
        if self.lock.acquire(False):
            try:
                self.values['dsp_max_work_ms'] = max(self.values['dsp_max_work_ms'], elapsed*1000)
                self.values['dsp_queue_delay_ms'] = max(0.0, queue_delay*1000)
            finally:
                self.lock.release()

    def peak(self, kind, value):
        if self.lock.acquire(False):
            try:
                self.values[kind] = max(self.values[kind],value)
            finally:
                self.lock.release()

    def device(self, latency):
        with self.lock:
            self.last_callback = None
            near, far = latency if isinstance(latency,tuple) else (0,latency)
            if not all(np.isfinite(value) and 0<=value<=5 for value in (near,far)):
                raise ValueError('Unsupported audio device latency')
            self.values.update(input_latency_ms=near*1000,output_latency_ms=far*1000)

    def snapshot(self):
        with self.lock:
            return dict(self.values)


class EchoFilter:
    """AEC3 with actual rendered PCM reference, plus conservative echo-only evidence."""

    def __init__(self, delay_ms=0):
        from pywebrtc_audio import AudioProcessor
        self.processor = AudioProcessor(sample_rate=RATE, echo_cancellation=True,
                                        noise_suppression=True, stream_delay_ms=delay_ms)
        self.far_active = deque(maxlen=150)
        self.active_reference_frames = 0
        self.far = deque(maxlen=150)  # 1.5 s including playback tail.
        self.near = deque(maxlen=20)
        self.capture_history = deque(maxlen=150)
        self.frames = 0
        self.echo_only = False
        self.correlation = 0.0
        self.linear_kernel = None
        self.linear_fit_error = None

    def process(self, near, far):
        near = np.asarray(near, dtype=np.float32).reshape(-1)
        far = np.asarray(far, dtype=np.float32).reshape(-1)
        if len(near) != FRAME or len(far) != FRAME:
            raise ValueError("AEC packets must contain exactly 10 ms of near/reference audio")
        if len(self.far_active) == self.far_active.maxlen:
            self.active_reference_frames -= self.far_active[0]
        active = bool(np.any(far))
        self.far_active.append(active)
        self.active_reference_frames += active
        self.far.append(far.copy())
        self.near.append(near.copy())
        self.capture_history.append(near.copy())
        self.frames += 1
        cleaned = self.processor.process(near, far)
        if not self.active_reference_frames:
            return near.copy()  # Never suppress a cold-start wake when no echo reference exists.
        if self.frames % 10 == 0:
            self.correlation = self.reference_correlation()
            self.echo_only = self.correlation >= 0.70
        if self.frames % 20 == 0 and self.echo_only and len(self.far) >= 100:
            self._fit_linear_path()
        if self.linear_kernel is not None:
            # AEC3's nonlinear suppressor can erase a short near-end wake syllable.
            # A reference-trained linear path preserves double-talk. Echo-only gating
            # remains independent; an invalid/unstable fit falls back to AEC3.
            history = np.concatenate(tuple(self.far))
            count = len(self.linear_kernel)
            if len(history) >= count + FRAME - 1:
                echo = np.convolve(history[-(count + FRAME - 1):], self.linear_kernel, mode="valid")
                return (near - echo).astype(np.float32)
        return np.asarray(cleaned, dtype=np.float32)

    def _fit_linear_path(self):
        # Frequency-domain system identification on an echo-dominated window only.
        # Near/far audio is memory-only and discarded with the session/device stream.
        far = np.concatenate(tuple(self.far))[-16000:].astype(np.float64)
        # Keep a longer capture history for identifying the acoustic impulse response.
        near = np.concatenate(tuple(self.capture_history))[-len(far):].astype(np.float64)
        if len(near) != len(far) or np.mean(far * far) < 1e-6:
            return
        size = 32768
        window = np.hanning(len(far))
        render = np.fft.rfft(far * window, size)
        capture = np.fft.rfft(near * window, size)
        power = np.abs(render) ** 2
        transfer = capture * render.conj() / (power + max(float(power.max()) * .0005, 1e-10))
        kernel = np.fft.irfft(transfer, size)[:4096]
        peak = float(np.max(np.abs(kernel)))
        if peak < 1e-5 or peak > 4:
            return
        # Refine the coarse FFT peaks against unwindowed samples. This avoids
        # attenuating plosive consonants when the render speech has spectral holes.
        candidates = np.abs(kernel).copy()
        delays = set()
        for _ in range(6):
            delay = int(np.argmax(candidates))
            if candidates[delay] < peak * .03:
                break
            delays.update(range(max(0, delay - 2), min(4096, delay + 3)))
            candidates[max(0, delay - 32):delay + 33] = 0
        delays = sorted(delays)
        target = near[4096:]
        design = np.column_stack([far[4096 - d:len(far) - d] for d in delays])
        gram = design.T @ design
        penalty = max(float(np.trace(gram)) / max(len(delays), 1) * 1e-7, 1e-10)
        coefficients = np.linalg.solve(gram + np.eye(len(delays)) * penalty, design.T @ target)
        kernel = np.zeros(4096)
        kernel[delays] = coefficients
        predicted = np.fft.irfft(np.fft.rfft(far, size) * np.fft.rfft(kernel, size), size)[:len(far)]
        valid = slice(4096, None)
        error = float(np.mean((near[valid] - predicted[valid]) ** 2) / max(np.mean(near[valid] ** 2), 1e-10))
        if error < .30:
            self.linear_kernel = kernel.astype(np.float32)
            self.linear_fit_error = error

    def reference_correlation(self):
        if len(self.near) < 10:
            return 0.0
        near = np.concatenate(tuple(self.near)).astype(np.float64)
        far = np.concatenate(tuple(self.far)).astype(np.float64)
        energy = float(near @ near)
        if energy < 1e-7 or len(far) < len(near):
            return 0.0
        # Positive/negative gain and arbitrary latency. No user audio is persisted.
        dots = np.correlate(far, near, mode="valid")
        squared = np.concatenate(([0.0], np.cumsum(far * far)))
        windows = squared[len(near):] - squared[:-len(near)]
        valid = windows > 1e-7
        if not valid.any():
            return 0.0
        return float(np.max(np.abs(dots[valid]) / np.sqrt(windows[valid] * energy)))


def default_device_pair(sd):
    """Prefer Windows WASAPI so capture/render share meaningful stream timestamps."""
    for api in sd.query_hostapis():
        if api["name"] == "Windows WASAPI" and api["default_output_device"] >= 0:
            return api["default_input_device"], api["default_output_device"]
    return tuple(sd.default.device)
