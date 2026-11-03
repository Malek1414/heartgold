import time
from src.dedupe import dedupe


def n(rs):
    return [r["n"] for r in dedupe(rs)]


def R(*emails):
    return [{"email": e, "n": i} for i, e in enumerate(emails)]


def test_gmail_dots_ignored():
    assert n(R("john.doe@gmail.com", "johndoe@gmail.com")) == [0]


def test_gmail_plus_ignored():
    assert n(R("jane+news@gmail.com", "jane@gmail.com")) == [0]


def test_googlemail_alias():
    assert n(R("bob@googlemail.com", "bob@gmail.com")) == [0]


def test_gmail_case():
    assert n(R("Bob.Smith@GMail.com", "bobsmith@gmail.com")) == [0]


def test_other_domain_dots_matter():
    assert n(R("john.doe@outlook.com", "johndoe@outlook.com")) == [0, 1]


def test_other_domain_plus_kept():
    assert n(R("a+b@corp.io", "a@corp.io")) == [0, 1]


def test_other_domain_case_of_domain_ignored():
    assert n(R("Sam@CORP.io", "Sam@corp.io")) == [0]


def test_whitespace():
    assert n(R("  x@y.com ", "x@y.com")) == [0]


def test_order_preserved():
    assert n(R("c@z.com", "a@z.com", "c@z.com", "b@z.com")) == [0, 1, 3]


def test_fast():
    recs = [{"email": f"u{i % 20000}@x.com", "n": i} for i in range(100000)]
    t = time.perf_counter()
    dedupe(recs)
    assert time.perf_counter() - t < 1.0
