from src.linebreak import break_opportunities


def test_spaces():
    assert break_opportunities("ab cd") == [3, 5]
