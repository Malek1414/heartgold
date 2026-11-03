from src.urljoin import resolve


def test_relative():
    assert resolve("http://a/b/c", "d") == "http://a/b/d"
