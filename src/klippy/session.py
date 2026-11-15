"""One shared, ephemeral follow-up clock across interpretation and playback."""

import itertools
import threading
import time
import uuid


class Session:
    def __init__(self, clock=time.monotonic, timeout=30):
        self.clock, self.timeout = clock, timeout
        self.lock = threading.RLock()
        self.deadline = 0.0
        self.holds = set()
        self.ids = itertools.count()
        self.session_id = None
        self.response_ready = False
        self.on_event = None
        self.events = []

    def snapshot(self):
        with self.lock:
            active = bool(self.holds) or self.clock() < self.deadline
            if not active and self.session_id is not None:
                self.clear("timeout")
            remaining = max(0.0, self.deadline - self.clock()) if active and not self.holds else 0.0
            result = {
                "session_id": self.session_id,
                "active": active,
                "held": bool(self.holds),
                "ready": active and self.response_ready and not self.holds,
                "remaining": remaining,
                "fraction": min(1.0, remaining / self.timeout) if self.timeout > 0 else 0.0,
            }
            events, self.events = self.events, []
        for event in events:
            if self.on_event:
                try:
                    self.on_event(*event)
                except Exception:
                    pass  # Optional diagnostics have no control authority.
        return result

    @property
    def until(self):
        with self.lock:
            return float("inf") if self.holds else self.deadline

    def touch(self):
        with self.lock:
            if not self.holds and self.session_id is not None and self.clock() >= self.deadline:
                self.clear("timeout")
            if self.session_id is None:
                self.session_id = uuid.uuid4().hex
            self.deadline = self.clock() + self.timeout

    def begin(self):
        with self.lock:
            if not self.holds and self.session_id is not None and self.clock() >= self.deadline:
                self.clear("timeout")
            token = next(self.ids)
            self.holds.add(token)
            if self.session_id is None:
                self.session_id = uuid.uuid4().hex
            self.response_ready = False
            return token

    def begin_active(self):
        """Hold an already-authorized conversation without opening an expired one."""
        with self.lock:
            return self.begin() if self.clock() < self.until else None

    def finish(self, token, *, refresh=True, response=False):
        with self.lock:
            if token in self.holds:
                self.holds.remove(token)
                if refresh:
                    self.deadline = self.clock() + self.timeout  # A held turn never expired while processing.
                if response:
                    self.response_ready = True

    def response_complete(self):
        with self.lock:
            if self.session_id is not None:
                self.touch()
                self.response_ready = True

    def clear(self, reason="cleared"):
        with self.lock:
            if self.session_id is not None:
                self.events = [*self.events, (self.session_id, reason)][-32:]
            self.session_id = None
            self.response_ready = False
            self.holds.clear()
            self.deadline = 0.0
