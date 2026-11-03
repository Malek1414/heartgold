import functools, re

_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
                 r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
                 r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$")


def parse(version):
    m = _RE.match(version)
    if not m:
        raise ValueError(f"invalid semver: {version!r}")
    return int(m[1]), int(m[2]), int(m[3]), m[4] or ""


def _pre_key(pre):
    if not pre:
        return (1,)
    return (0, tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in pre.split(".")))


def compare(a, b):
    pa, pb = parse(a), parse(b)
    ka, kb = (pa[:3], _pre_key(pa[3])), (pb[:3], _pre_key(pb[3]))
    return (ka > kb) - (ka < kb)


def sort_versions(versions):
    return sorted(versions, key=functools.cmp_to_key(compare))
