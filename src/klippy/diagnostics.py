"""Bounded in-memory monotonic timings; never stores utterances or endpoints."""
import contextvars
import itertools
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager

current = contextvars.ContextVar("reaction", default=None)


class Timings:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.Lock()
        self.ids = itertools.count(1)
        self.rows = OrderedDict()

    def new(self, speech_end=None):
        with self.lock:
            key = next(self.ids)
            self.rows[key] = {"origin": self.clock() if speech_end is None else speech_end, "stages": {}}
            while len(self.rows) > 32:
                self.rows.popitem(last=False)
            return key

    def mark(self, stage, key=None, *, at=None):
        key = current.get() if key is None else key
        with self.lock:
            if key in self.rows:
                row = self.rows[key]
                row["stages"].setdefault(stage, round(1000 * ((self.clock() if at is None else at) - row["origin"]), 2))
                if stage == "first_audio_render" and "tts_first_pcm" in row["stages"]:
                    row["stages"]["playback_queue"] = round(row["stages"][stage] - row["stages"]["tts_first_pcm"], 2)

    def duration(self, stage, seconds, key=None):
        key = current.get() if key is None else key
        with self.lock:
            if key in self.rows:
                self.rows[key]["stages"][stage] = round(seconds * 1000, 2)

    @contextmanager
    def span(self, stage):
        start = self.clock()
        try:
            yield
        finally:
            self.duration(stage, self.clock() - start)

    def snapshot(self):
        with self.lock:
            return [{"reaction": k, "milliseconds": dict(v["stages"])} for k, v in self.rows.items()]

    def compact(self):
        rows = self.snapshot()
        return ("Latest local reaction (ms): " + "; ".join(f"{k}: {v:g}" for k, v in rows[-1]["milliseconds"].items())
                if rows else "No reaction measured yet. Timings stay in memory; no transcripts are recorded.")


timings = Timings()
