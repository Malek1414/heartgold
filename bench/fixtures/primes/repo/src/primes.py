"""Number theory helpers."""


def count_primes(n):
    """Number of primes p with p <= n."""
    count = 0
    for k in range(2, n + 1):
        d = 2
        is_prime = True
        while d * d <= k:
            if k % d == 0:
                is_prime = False
                break
            d += 1
        if is_prime:
            count += 1
    return count
