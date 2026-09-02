"""Sliding-window rate limiter.

Protects the authentication endpoints against credential-stuffing. State is
kept in memory for the prototype; a Redis backend would be substituted for a
multi-replica deployment (the interface is identical).
"""
import threading
import time
from collections import defaultdict, deque

from .config import settings


class SlidingWindowLimiter:
    def __init__(self, max_events: int, window_seconds: int) -> None:
        self.max_events = max_events
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.max_events:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter(settings.RATE_LIMIT_MAX, settings.RATE_LIMIT_WINDOW)
