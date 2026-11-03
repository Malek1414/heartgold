import random, time
from src.lcs import lcs_length
rnd = random.Random(7)
a = "".join(rnd.choice("acgt") for _ in range(2500))
b = "".join(rnd.choice("acgt") for _ in range(2500))
t = time.perf_counter(); lcs_length(a, b); print(time.perf_counter() - t)
