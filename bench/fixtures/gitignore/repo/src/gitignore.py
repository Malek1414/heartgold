"""Decide which files our sync tool skips, using .gitignore rules."""
import fnmatch


def ignored(patterns, paths):
    """Return the subset of file `paths` (relative, '/'-separated) that the
    .gitignore lines `patterns` exclude."""
    out = set()
    for path in paths:
        name = path.split("/")[-1]
        for p in patterns:
            p = p.strip()
            if not p or p.startswith("#"):
                continue
            if fnmatch.fnmatch(name, p) or fnmatch.fnmatch(path, p):
                out.add(path)
    return out
