from src.semver import compare, sort_versions


def test_core_order():
    assert compare("1.0.0", "2.0.0") == -1
    assert compare("2.1.0", "2.0.9") == 1
    assert compare("1.2.3", "1.2.3") == 0


def test_sort_basic():
    assert sort_versions(["1.10.0", "1.2.0", "1.9.0"]) == ["1.2.0", "1.9.0", "1.10.0"]
