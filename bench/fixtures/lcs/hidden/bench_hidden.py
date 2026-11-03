import random, time
from src.lcs import lcs_length
rnd = random.Random(99)
pairs = [("".join(rnd.choice(al) for _ in range(n)), "".join(rnd.choice(al) for _ in range(m)))
         for al, n, m in [("abcdefghijklmnopqrstuvwxyz", 2200, 2400), ("01", 2600, 2000), ("acgté", 1800, 2300)]]
t = time.perf_counter()
for a, b in pairs:
    lcs_length(a, b)
print(time.perf_counter() - t)
