from src.gitignore import ignored


def test_extension():
    assert ignored(["*.log"], ["a.log", "b.txt"]) == {"a.log"}
