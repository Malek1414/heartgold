from src.fuzzy import distance, search


def test_distance_basic():
    assert distance("kitten", "sitting") == 3
    assert distance("", "abc") == 3


def test_search_basic():
    assert search("helo", ["hello", "world", "help"])[:2] in (["hello", "help"], ["help", "hello"])
