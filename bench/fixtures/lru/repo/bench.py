import random, time
from src.lru import LRUCache

rnd = random.Random(1)
keys = [rnd.randint(0, 20000) for _ in range(200000)]
c = LRUCache(5000)
t = time.perf_counter()
for k in keys:
    if c.get(k) is None:
        c.put(k, k)
print(time.perf_counter() - t)
