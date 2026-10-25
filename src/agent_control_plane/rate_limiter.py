"""Per-tool, per-session rate limiting with an injectable clock for tests."""
from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    """Sliding-window limiter. Limits are calls per `window_seconds`.

    `limits` maps tool_name -> max calls; "*" sets a default for all tools.
    State is keyed by (session_id, tool_name) so one noisy session cannot
    starve others -- the same shape as per-case budgets in production agents.
    """

    def __init__(self, limits: dict[str, int] | None = None, window_seconds: float = 3600.0, clock=time.time):
        self.limits = limits or {"*": 20}
        self.window = window_seconds
        self.clock = clock
        self._events: dict[tuple[str, str], deque] = defaultdict(deque)

    def _limit_for(self, tool: str) -> int:
        return self.limits.get(tool, self.limits.get("*", 20))

    def _prune(self, key):
        now = self.clock()
        dq = self._events[key]
        while dq and now - dq[0] > self.window:
            dq.popleft()
        return dq

    def check(self, session_id: str, tool: str) -> bool:
        return len(self._prune((session_id, tool))) < self._limit_for(tool)

    def record(self, session_id: str, tool: str) -> None:
        self._events[(session_id, tool)].append(self.clock())

    def remaining(self, session_id: str, tool: str) -> int:
        return max(0, self._limit_for(tool) - len(self._prune((session_id, tool))))
