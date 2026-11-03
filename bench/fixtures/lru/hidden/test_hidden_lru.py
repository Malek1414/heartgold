from src.lru import LRUCache


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_basic_still_works():
    c = LRUCache(2)
    c.put("a", 1); c.put("b", 2); c.get("a"); c.put("c", 3)
    assert c.get("b") is None and c.get("a") == 1


def test_update_refreshes_recency():
    c = LRUCache(2)
    c.put("a", 1); c.put("b", 2); c.put("a", 10); c.put("c", 3)
    assert c.get("a") == 10 and c.get("b") is None


def test_falsy_values():
    c = LRUCache(2)
    c.put("z", 0)
    assert c.get("z", "missing") == 0
    c.put("n", None)
    assert c.get("n", "missing") is None


def test_default_ttl():
    clk = Clock()
    c = LRUCache(3, ttl=5, clock=clk)
    c.put("a", 1)
    clk.t = 4.9
    assert c.get("a") == 1
    clk.t = 5.1
    assert c.get("a") is None


def test_per_entry_ttl_overrides():
    clk = Clock()
    c = LRUCache(3, ttl=100, clock=clk)
    c.put("a", 1, ttl=1)
    c.put("b", 2)
    clk.t = 2
    assert c.get("a") is None and c.get("b") == 2


def test_expired_do_not_count_toward_capacity():
    clk = Clock()
    c = LRUCache(2, clock=clk)
    c.put("a", 1, ttl=1)
    c.put("b", 2)
    clk.t = 5
    c.put("c", 3)
    assert c.get("b") == 2 and c.get("c") == 3
    assert len(c) == 2


def test_capacity_one():
    c = LRUCache(1)
    c.put(1, 1); c.put(2, 2)
    assert c.get(1) is None and c.get(2) == 2 and len(c) == 1


def test_big_is_fast():
    import time
    c = LRUCache(50000)
    t = time.perf_counter()
    for i in range(200000):
        c.put(i, i)
        c.get(i - 10)
    assert time.perf_counter() - t < 2.0
