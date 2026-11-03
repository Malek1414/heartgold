import heapq, time
from collections import OrderedDict

_MISSING = object()


class LRUCache:
    def __init__(self, capacity, ttl=None, clock=time.monotonic):
        self.capacity, self.ttl, self.clock = capacity, ttl, clock
        self.data = OrderedDict()
        self._heap = []  # (expiry, key), lazily invalidated

    def _purge(self):
        now = self.clock()
        h = self._heap
        while h and h[0][0] <= now:
            exp, key = heapq.heappop(h)
            item = self.data.get(key, _MISSING)
            if item is not _MISSING and item[1] == exp:
                del self.data[key]

    def get(self, key, default=None):
        item = self.data.get(key, _MISSING)
        if item is _MISSING:
            return default
        value, exp = item
        if exp is not None and exp <= self.clock():
            del self.data[key]
            return default
        self.data.move_to_end(key)
        return value

    def put(self, key, value, ttl=None):
        ttl = self.ttl if ttl is None else ttl
        exp = None if ttl is None else self.clock() + ttl
        if key in self.data:
            self.data.move_to_end(key)
        elif len(self.data) >= self.capacity:
            self._purge()
            if len(self.data) >= self.capacity:
                self.data.popitem(last=False)
        self.data[key] = (value, exp)
        if exp is not None:
            heapq.heappush(self._heap, (exp, key))

    def __len__(self):
        self._purge()
        return len(self.data)
