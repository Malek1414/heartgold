import time
from src.nqueens import count_solutions
t = time.perf_counter()
assert count_solutions(10) == 724
assert count_solutions(11) == 2680
print(time.perf_counter() - t)
