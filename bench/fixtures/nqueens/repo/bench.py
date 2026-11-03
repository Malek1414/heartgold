import time
from src.nqueens import count_solutions
t = time.perf_counter(); count_solutions(9); print(time.perf_counter() - t)
