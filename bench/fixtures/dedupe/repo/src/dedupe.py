"""Record deduplication."""


def normalize(email):
    return email.strip().lower()


def dedupe(records):
    """Remove duplicate records by email, keeping the first occurrence in order."""
    out = []
    for r in records:
        if not any(normalize(o["email"]) == normalize(r["email"]) for o in out):
            out.append(r)
    return out
