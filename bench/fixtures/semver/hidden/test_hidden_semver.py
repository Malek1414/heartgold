import pytest
from src.semver import compare, sort_versions


def test_release_beats_prerelease():
    assert compare("1.0.0-alpha", "1.0.0") == -1
    assert compare("1.0.0", "1.0.0-rc.1") == 1


def test_spec_example_chain():
    chain = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta",
             "1.0.0-beta.2", "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"]
    for lo, hi in zip(chain, chain[1:]):
        assert compare(lo, hi) == -1, (lo, hi)
        assert compare(hi, lo) == 1, (hi, lo)


def test_numeric_identifiers_compare_numerically():
    assert compare("1.0.0-beta.2", "1.0.0-beta.11") == -1


def test_numeric_lower_than_alphanumeric():
    assert compare("1.0.0-1", "1.0.0-alpha") == -1


def test_build_metadata_ignored():
    assert compare("1.0.0+build.1", "1.0.0+build.2") == 0
    assert compare("1.0.0-alpha+001", "1.0.0-alpha") == 0


def test_hyphen_inside_prerelease():
    assert compare("1.0.0-x-y-z.1", "1.0.0-x-y-z.2") == -1


def test_build_with_hyphen():
    assert compare("1.0.0+21AF26D3--117B344092BD", "1.0.0") == 0


def test_sort_mixed():
    vs = ["1.0.0", "1.0.0-rc.1", "1.0.0-alpha", "0.9.9", "1.0.0-beta.11", "1.0.0-beta.2"]
    assert sort_versions(vs) == ["0.9.9", "1.0.0-alpha", "1.0.0-beta.2",
                                 "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"]


def test_invalid_rejected():
    for bad in ["1.0", "01.0.0", "1.0.0-", "1.0.0-01", "a.b.c"]:
        with pytest.raises(ValueError):
            compare(bad, "1.0.0")
