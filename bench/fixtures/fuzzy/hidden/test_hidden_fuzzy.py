import random, string, time
from src.fuzzy import distance, search


def osa(a, b):
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[len(a)][len(b)]


def test_transposition_costs_one():
    assert distance("teh", "the") == 1
    assert distance("ab", "ba") == 1


def test_osa_not_unrestricted():
    # OSA: "ca" -> "abc" is 3 (unrestricted Damerau gives 2)
    assert distance("ca", "abc") == 3


def test_matches_reference_random():
    rnd = random.Random(11)
    for _ in range(300):
        a = "".join(rnd.choice("abcd") for _ in range(rnd.randint(0, 7)))
        b = "".join(rnd.choice("abcd") for _ in range(rnd.randint(0, 7)))
        assert distance(a, b) == osa(a, b), (a, b)


def test_long_strings_ok():
    a = "a" * 300 + "xy"
    b = "a" * 300 + "yx"
    assert distance(a, b) == 1


def test_unicode():
    assert distance("café", "cafe") == 1


def test_ordering_ties_alphabetical():
    assert search("cat", ["cut", "bat", "act", "cat"]) == ["cat", "act", "bat", "cut"]


def test_search_respects_max():
    assert search("abc", ["abcdef", "abd"], max_distance=1) == ["abd"]


def test_search_fast():
    rnd = random.Random(5)
    words = ["".join(rnd.choice(string.ascii_lowercase) for _ in range(rnd.randint(5, 12))) for _ in range(20000)]
    t = time.perf_counter()
    for _ in range(10):
        search("qwertyu", words)
    assert time.perf_counter() - t < 3.0
