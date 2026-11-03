Our package index must order and display versions exactly the way pip does:
implement full PEP 440 ("Version Identification and Dependency Specification")
parsing, normalization (`str(Version(s))` returns the normalized form) and
ordering, including epochs, pre-, post- and dev-releases, local versions and all
the alternative spellings PEP 440 says to accept. Invalid versions raise
`InvalidVersion`. Equal versions must hash equal. Pure Python standard library
only: `packaging` and other third-party modules are not available in production.
Keep `Version` and `InvalidVersion` in `src/pep440.py`.
