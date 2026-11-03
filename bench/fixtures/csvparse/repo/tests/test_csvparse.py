from src.csvparse import parse


def test_simple():
    assert parse("a,b,c\n1,2,3\n") == [["a", "b", "c"], ["1", "2", "3"]]


def test_quoted_simple():
    assert parse('"a","b"\n') == [["a", "b"]]


def test_no_stdlib_csv():
    import src.csvparse as m
    assert "csv" not in getattr(m, "__dict__", {}) or m.__dict__["csv"] is None
