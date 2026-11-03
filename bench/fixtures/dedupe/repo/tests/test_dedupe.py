from src.dedupe import dedupe


def test_keeps_first():
    rs = [{"email": "a@x.com", "n": 1}, {"email": "A@x.com ", "n": 2}, {"email": "b@x.com", "n": 3}]
    assert [r["n"] for r in dedupe(rs)] == [1, 3]
