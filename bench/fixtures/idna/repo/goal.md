`to_ascii(domain)` must behave exactly like the reference IDNA 2008 + UTS #46
processing used by the Python `idna` package (`idna.encode(domain,
uts46=True, transitional=False)`, Unicode 16.0.0 data): UTS #46 mapping
(case folding, compatibility forms, alternate dot separators), NFC, the IDNA
2008 validity rules (DISALLOWED/CONTEXTJ/CONTEXTO code points, hyphen rules,
combining-mark start, the Bidi rule of RFC 5893), Punycode (RFC 3492), label and
name length limits. Invalid names raise ValueError. Standard library only (the
`idna` package and the `encodings.idna` codec are not allowed), no network at
runtime; vendoring data files into the repo is fine.
