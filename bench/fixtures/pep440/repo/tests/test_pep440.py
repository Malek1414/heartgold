from src.pep440 import Version


def test_simple_order():
    assert Version("1.2") < Version("1.10")
    assert str(Version("2.0.1")) == "2.0.1"
