from src.primes import count_primes


def test_small():
    assert count_primes(30) == 10
