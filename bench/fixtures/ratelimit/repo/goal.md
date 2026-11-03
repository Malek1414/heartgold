The limiter must guarantee that no key ever gets more than `limit` requests in
ANY rolling `window`-second interval (the current one lets bursts through at
window boundaries). Memory per key must stay bounded (O(limit) or better), and
idle keys must not leak memory forever. Keep `RateLimiter(limit, window, clock)`
and `allow(key) -> bool`.
