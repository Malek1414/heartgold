`ignored(patterns, paths)` must return exactly the files git itself would treat
as ignored for a root `.gitignore` containing `patterns` (one line each) - same
semantics as gitignore(5): negation, directory-only patterns, anchoring,
`**`, character classes, escaping, trailing spaces, comments, and the rule about
files inside excluded directories. `paths` are files relative to the repo root.
Do not shell out to git, and do not use the pathspec library.
