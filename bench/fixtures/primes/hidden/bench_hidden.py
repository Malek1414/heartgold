import time
from src.primes import count_primes
t = time.perf_counter()
for n in (2_000_003, 1_234_567, 3_000_017):
    count_primes(n)
print(time.perf_counter() - t)
