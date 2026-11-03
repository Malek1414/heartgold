from src.ratelimit import RateLimiter


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_blocks_over_limit():
    c = Clock()
    rl = RateLimiter(3, 10, clock=c)
    assert [rl.allow("u") for _ in range(4)] == [True, True, True, False]


def test_keys_independent():
    c = Clock()
    rl = RateLimiter(1, 10, clock=c)
    assert rl.allow("a") and rl.allow("b")
