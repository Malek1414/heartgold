import random, string, time
from src.fuzzymatch import within
rnd = random.Random(2)
words = ["".join(rnd.choice(string.ascii_lowercase) for _ in range(rnd.randint(4, 11))) for _ in range(30000)]
t = time.perf_counter()
for q in ("example", "zebra", "kitchen"):
    within(q, words, 2)
print(time.perf_counter() - t)
