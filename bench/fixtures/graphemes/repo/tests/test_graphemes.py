from src.graphemes import graphemes


def test_combining():
    assert graphemes("e\u0301x") == ["e\u0301", "x"]
