Make `parse` fully compliant with RFC 4180 (Common Format and MIME Type for CSV
Files). The stdlib `csv` module must not be used. Keep the signature
`parse(text) -> list[list[str]]`.
