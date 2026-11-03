from src.fuzzymatch import within


def test_small():
    assert within("cat", ["bat", "cart", "dog", "cat"], 1) == [(0, "cat"), (1, "bat"), (1, "cart")]
