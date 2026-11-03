import random, string, time
from src.fuzzymatch import within
rnd = random.Random(77)
words = ["".join(rnd.choice("etaoinshrdlu") for _ in range(rnd.randint(3, 13))) for _ in range(60000)]
t = time.perf_counter()
for q, k in (("relations", 2), ("hound", 1), ("tradition", 3)):
    within(q, list(words), k)
print(time.perf_counter() - t)
