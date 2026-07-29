"""Minimal in-process per-key rate limiter.

In-memory only: state lives in this module's process and resets on restart
or on a demo reset. That's a deliberate scope limit, not an oversight — this
is abuse mitigation for a single-instance hackathon deployment (the public
URL will get probed), not a substitute for a real distributed limiter behind
multiple workers or replicas.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock


class InMemoryRateLimiter:
    """Sliding-window counter: at most `limit` calls per `window_seconds` per key."""

    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            q = self._hits[key]
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
