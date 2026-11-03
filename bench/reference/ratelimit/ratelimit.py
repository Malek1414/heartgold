import time
from collections import deque


class RateLimiter:
    def __init__(self, limit, window, clock=time.monotonic):
        self.limit, self.window, self.clock = limit, window, clock
        self.logs = {}
        self._last_sweep = None

    def allow(self, key):
        now = self.clock()
        if self._last_sweep is None or now - self._last_sweep >= self.window:
            for k in [k for k, q in self.logs.items() if not q or now - q[-1] >= self.window]:
                del self.logs[k]
            self._last_sweep = now
        q = self.logs.setdefault(key, deque())
        while q and now - q[0] >= self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True
