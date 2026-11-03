from src.nqueens import count_solutions


def test_small():
    assert count_solutions(6) == 4
