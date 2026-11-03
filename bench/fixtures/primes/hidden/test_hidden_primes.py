import json, pathlib, pytest
C = json.loads((pathlib.Path(__file__).parent.parent / "_hidden_tests" / "cases.json").read_text())


from src.primes import count_primes


@pytest.mark.parametrize("n,expected", C)
def test_same_result(n, expected):
    assert count_primes(n) == expected


def test_big_known():
    assert count_primes(10_000_000) == 664579
