"""One shared, ephemeral follow-up clock across interpretation and playback."""
import itertools
import threading
import time


class Session:
    def __init__(self, clock=time.monotonic, timeout=30):
        self.clock, self.timeout = clock, timeout
        self.lock = threading.RLock()
        self.deadline = 0.0
        self.holds = set()
        self.ids = itertools.count()

    @property
    def until(self):
        with self.lock:
            return float("inf") if self.holds else self.deadline

    def touch(self):
        with self.lock:
            self.deadline = self.clock() + self.timeout

    def begin(self):
        with self.lock:
            token = next(self.ids)
            self.holds.add(token)
            return token

    def begin_active(self):
        """Hold an already-authorized conversation without opening an expired one."""
        with self.lock:
            return self.begin() if self.clock() < self.until else None

    def finish(self, token, *, refresh=True):
        with self.lock:
            if token in self.holds:
                self.holds.remove(token)
                if refresh:
                    self.touch()

    def clear(self):
        with self.lock:
            self.holds.clear()
            self.deadline = 0.0
