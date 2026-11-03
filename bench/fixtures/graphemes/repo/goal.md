`graphemes(text)` must split text into extended grapheme clusters exactly as
Unicode Standard Annex #29 specifies for Unicode 16.0.0 (all GB rules, including
emoji ZWJ sequences, regional-indicator pairs, Hangul syllables, prepend and
the Indic conjunct rule). Note Python's `unicodedata` may be an older Unicode
version than 16.0.0. Standard library only (no `regex`, no `grapheme` package)
and no network access at runtime; vendoring data files into the repo is fine.
