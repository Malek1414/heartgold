Make `can_fetch` follow RFC 9309 (Robots Exclusion Protocol) the way Google's
robots.txt parser does: user-agent group selection and merging (product token,
case-insensitive, version suffix ignored, `*` fallback), most-specific (longest)
match wins, Allow vs Disallow ties, `*` and `$` in patterns, empty Disallow,
case-insensitive directives, CRLF, comments, unknown lines, and percent-encoding
normalization when matching paths. Standard library only (no protego, no
urllib.robotparser).
