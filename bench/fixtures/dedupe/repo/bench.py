import random, time
from src.dedupe import dedupe

rnd = random.Random(2)
recs = [{"email": f"user{rnd.randint(0, 4000)}@Example.com", "n": i} for i in range(20000)]
t = time.perf_counter()
dedupe(recs)
print(time.perf_counter() - t)
