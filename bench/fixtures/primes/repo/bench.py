import time
from src.primes import count_primes
t = time.perf_counter(); count_primes(300000); print(time.perf_counter() - t)
