"""Testable duplex audio primitives. No model, network, device, or printer control here."""
import threading
from collections import deque

import numpy as np

RATE = 16000
FRAME = 160  # WebRTC AEC uses 10 ms frames.


def resample(samples, source_rate, target_rate=RATE):
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    if source_rate == target_rate or not len(samples):
        return samples.copy()
    length = round(len(samples) * target_rate / source_rate)
    return np.interp(np.arange(length) * source_rate / target_rate,
                     np.arange(len(samples)), samples).astype(np.float32)


class Playback:
    """Generation-bound PCM buffer. Interrupting flushes the next render frame immediately."""

    def __init__(self):
        self.lock = threading.Lock()
        self.generation = 0
        self.blocks = deque()
        self.offset = 0
        self.remaining = 0

    def interrupt(self):
        with self.lock:
            self.generation += 1
            self.blocks.clear()
            self.offset = self.remaining = 0
            return self.generation

    def enqueue(self, samples, generation):
        samples = np.asarray(samples, dtype=np.float32).reshape(-1)
        with self.lock:
            if generation != self.generation:
                return False
            if self.remaining + len(samples) > RATE * 60:
                raise ValueError("Speech playback buffer exceeded its limit")
            self.blocks.append(samples.copy())
            self.remaining += len(samples)
            return True

    def render(self, size=FRAME):
        output = np.zeros(size, dtype=np.float32)
        with self.lock:
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
        return output


class EchoFilter:
    """AEC3 with actual rendered PCM reference, plus conservative echo-only evidence."""

    def __init__(self, delay_ms=0):
        from pywebrtc_audio import AudioProcessor
        self.processor = AudioProcessor(sample_rate=RATE, echo_cancellation=True,
                                        noise_suppression=True, stream_delay_ms=delay_ms)
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
        self.far.append(far.copy())
        self.near.append(near.copy())
        self.capture_history.append(near.copy())
        self.frames += 1
        cleaned = self.processor.process(near, far)
        if not any(np.any(frame) for frame in self.far):
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
