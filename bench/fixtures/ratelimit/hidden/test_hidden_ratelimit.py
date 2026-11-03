import random
from src.ratelimit import RateLimiter


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_no_boundary_burst():
    c = Clock()
    rl = RateLimiter(5, 10, clock=c)
    c.t = 9.9
    assert sum(rl.allow("u") for _ in range(5)) == 5
    c.t = 10.1
    assert sum(rl.allow("u") for _ in range(5)) == 0


def test_recovers_after_window():
    c = Clock()
    rl = RateLimiter(2, 10, clock=c)
    c.t = 0
    assert rl.allow("u") and rl.allow("u")
    c.t = 10.01
    assert rl.allow("u")


def test_rolling_window_property_random():
    rnd = random.Random(7)
    for trial in range(30):
        c = Clock()
        limit, window = rnd.randint(1, 6), rnd.choice([1.0, 5.0, 10.0])
        rl = RateLimiter(limit, window, clock=c)
        allowed = []
        t = 0.0
        for _ in range(400):
            t += rnd.random() * window / 4
            c.t = t
            if rl.allow("k"):
                allowed.append(t)
        for i, ti in enumerate(allowed):
            inside = [x for x in allowed[i:] if x - ti < window]
            assert len(inside) <= limit, (limit, window, trial)
        assert len(allowed) > 0


def test_not_too_strict():
    # evenly spaced requests at exactly the allowed rate must all pass
    c = Clock()
    rl = RateLimiter(4, 8, clock=c)
    ok = 0
    for i in range(40):
        c.t = i * 2.0 + 0.001
        ok += rl.allow("u")
    assert ok >= 38


def test_idle_keys_do_not_leak():
    c = Clock()
    rl = RateLimiter(3, 1, clock=c)
    for i in range(5000):
        c.t = i * 2.0
        rl.allow(f"user{i}")
    size = 0
    for v in vars(rl).values():
        if isinstance(v, dict):
            size += len(v)
    assert size < 500
