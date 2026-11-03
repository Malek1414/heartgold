"""Tiny semantic version helper."""


def parse(version):
    core = version.split("-")[0]
    major, minor, patch = core.split(".")
    pre = version.split("-")[1] if "-" in version else ""
    return int(major), int(minor), int(patch), pre


def compare(a, b):
    """Return -1 if a < b, 0 if equal, 1 if a > b."""
    pa, pb = parse(a), parse(b)
    if pa[:3] != pb[:3]:
        return -1 if pa[:3] < pb[:3] else 1
    if pa[3] == pb[3]:
        return 0
    return -1 if pa[3] < pb[3] else 1


def sort_versions(versions):
    import functools
    return sorted(versions, key=functools.cmp_to_key(compare))
