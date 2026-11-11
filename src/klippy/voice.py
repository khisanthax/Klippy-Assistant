"""Local speech adapters. AEC is a release gate: hands-free while speaking is disabled in preview."""
from __future__ import annotations

import queue
import threading
import time
from pathlib import Path

from .models import verify_pack


class SherpaBackend:
    def __init__(self, root: Path, config, sensitivity=0.25):
        import sherpa_onnx as so
        verify_pack(root)
        def absolute(values):
            return {key: str(root / value) for key, value in values.items()}
        self.kws = so.KeywordSpotter(**absolute(config["wake"]), keywords_threshold=sensitivity, num_threads=1)
        self.stream = self.kws.create_stream()
        self.asr = so.OfflineRecognizer.from_whisper(**absolute(config["asr"]), num_threads=2)
        vits = so.OfflineTtsVitsModelConfig(**absolute(config["tts"]))
        self.tts = so.OfflineTts(so.OfflineTtsConfig(model=so.OfflineTtsModelConfig(vits=vits, num_threads=2)))

    def wake(self, samples):
        self.stream.accept_waveform(16000, samples)
        while self.kws.is_ready(self.stream):
            self.kws.decode_stream(self.stream)
        if self.kws.get_result(self.stream):
            self.kws.reset_stream(self.stream)
            return True
        return False

    def transcribe(self, samples):
        stream = self.asr.create_stream()
        stream.accept_waveform(16000, samples)
        self.asr.decode_stream(stream)
        return stream.result.text

    def synthesize(self, text):
        return self.tts.generate(text)


class VoiceLoop:
    """Default device capture; bounded queue and utterances. No audio/transcript persistence."""

    def __init__(self, backend, on_text, on_state):
        self.backend, self.on_text, self.on_state = backend, on_text, on_state
        self.enabled = threading.Event()
        self.closed = threading.Event()
        self.speaking = threading.Event()
        self.stop_speech = threading.Event()
        self.audio = queue.Queue(maxsize=64)
        self.thread = None
        self.until = 0.0

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def interrupt(self):
        import sounddevice as sd
        self.stop_speech.set()
        sd.stop()
        self.speaking.clear()

    def close(self):
        self.closed.set()
        self.enabled.set()
        self.interrupt()
        if self.thread:
            self.thread.join(timeout=3)

    def speak(self, text):
        import sounddevice as sd
        self.stop_speech.clear()
        self.speaking.set()
        try:
            audio = self.backend.synthesize(text)
            if not self.stop_speech.is_set():
                sd.play(audio.samples, audio.sample_rate, blocking=True)
        finally:
            self.speaking.clear()
            # Discard acoustic tail so synthesized confirmation can never confirm itself.
            self.until = time.monotonic() + 0.7
            while not self.audio.empty():
                try:
                    self.audio.get_nowait()
                except queue.Empty:
                    break

    def _capture(self, data, frames, timing, status):
        if not self.enabled.is_set() or self.speaking.is_set() or time.monotonic() < self.until:
            return
        try:
            self.audio.put_nowait(data[:, 0].copy())
        except queue.Full:
            pass

    def _run(self):
        import numpy as np
        import sounddevice as sd
        while not self.closed.is_set():
            self.enabled.wait(0.2)
            if not self.enabled.is_set() or self.closed.is_set():
                continue
            try:
                device = sd.query_devices(kind="input")["name"]
                with sd.InputStream(samplerate=16000, channels=1, dtype="float32", blocksize=1600,
                                    callback=self._capture):
                    listening_until, frames, silence = 0.0, [], 0
                    while self.enabled.is_set() and not self.closed.is_set():
                        if sd.query_devices(kind="input")["name"] != device:
                            break  # Reopen on a Windows default input-device change.
                        try:
                            block = self.audio.get(timeout=0.3)
                        except queue.Empty:
                            continue
                        if self.speaking.is_set():
                            frames.clear()
                            continue
                        if time.monotonic() > listening_until:
                            frames.clear()
                            if self.backend.wake(block):
                                listening_until = time.monotonic() + 30
                                self.on_state("Listening")
                            continue
                        energy = float(np.sqrt(np.mean(block * block)))
                        if energy > 0.01 or frames:
                            frames.append(block)
                            silence = silence + 1 if energy <= 0.01 else 0
                        if frames and (silence >= 8 or len(frames) >= 150):
                            samples = np.concatenate(frames)
                            frames.clear()
                            silence = 0
                            text = self.backend.transcribe(samples)
                            if text.strip():
                                self.on_text("Klippy " + text)
                                listening_until = time.monotonic() + 30
            except Exception:
                self.on_state("Microphone or speech engine unavailable; retrying safely")
                self.closed.wait(2)
