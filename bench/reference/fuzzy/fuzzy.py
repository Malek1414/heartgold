def distance(a, b, limit=None):
    la, lb = len(a), len(b)
    prev2, prev = None, list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        ai = a[i - 1]
        for j in range(1, lb + 1):
            cost = 0 if ai == b[j - 1] else 1
            v = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and ai == b[j - 2] and a[i - 2] == b[j - 1]:
                v = min(v, prev2[j - 2] + 1)
            cur[j] = v
        if limit is not None and min(cur) > limit:
            return limit + 1
        prev2, prev = prev, cur
    return prev[lb]


def search(query, words, max_distance=2):
    out = []
    lq = len(query)
    for w in words:
        if abs(len(w) - lq) > max_distance:
            continue
        d = distance(query, w, max_distance)
        if d <= max_distance:
            out.append((d, w))
    out.sort()
    return [w for _, w in out]
