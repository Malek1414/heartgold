from src.lcs import lcs_length


def test_small():
    assert lcs_length("ABCBDAB", "BDCABA") == 4
