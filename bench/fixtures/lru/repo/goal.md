Make every cache operation O(1) and add optional per-entry TTL expiry:
`LRUCache(capacity, ttl=None, clock=time.monotonic)` and `put(key, value, ttl=None)`
(per-entry ttl overrides the default). Expired entries must never be returned and
must not count toward capacity. `bench.py` prints seconds (lower is better).
