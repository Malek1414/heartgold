"""Request rate limiter: at most `limit` requests per `window` seconds per key."""
import time


class RateLimiter:
    def __init__(self, limit, window, clock=time.monotonic):
        self.limit = limit
        self.window = window
        self.clock = clock
        self.counts = {}

    def allow(self, key):
        now = self.clock()
        bucket = int(now // self.window)
        start, count = self.counts.get(key, (bucket, 0))
        if start != bucket:
            start, count = bucket, 0
        if count >= self.limit:
            return False
        self.counts[key] = (start, count + 1)
        return True
