"""Typo-tolerant word lookup."""


def distance(a, b):
    """Edit distance between a and b."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    cost = 0 if a[-1] == b[-1] else 1
    return min(distance(a[:-1], b) + 1,
               distance(a, b[:-1]) + 1,
               distance(a[:-1], b[:-1]) + cost)


def search(query, words, max_distance=2):
    """Return words within max_distance of query, closest first."""
    scored = [(distance(query, w), w) for w in words]
    return [w for d, w in sorted(scored) if d <= max_distance]
