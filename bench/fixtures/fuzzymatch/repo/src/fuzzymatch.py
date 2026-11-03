"""Spell-check candidates."""


def _dist(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def within(query, words, k):
    """All words whose Levenshtein distance to query is <= k, as (distance, word)
    pairs sorted by distance then word."""
    out = [(_dist(query, w), w) for w in words]
    return sorted((d, w) for d, w in out if d <= k)
