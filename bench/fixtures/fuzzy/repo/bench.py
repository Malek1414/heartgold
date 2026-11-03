import random, string, time
from src.fuzzy import search

rnd = random.Random(3)
words = ["".join(rnd.choice(string.ascii_lowercase) for _ in range(rnd.randint(6, 10))) for _ in range(3000)]
queries = [w[:2] + w[3:] for w in rnd.sample(words, 20)]
t = time.perf_counter()
for q in queries:
    search(q, words)
print(time.perf_counter() - t)
