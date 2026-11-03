from src.idna import to_ascii


def test_ascii_lowercased():
    assert to_ascii("Example.COM") == "example.com"
