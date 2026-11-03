"""Domain helpers for our mail server."""


def to_ascii(domain):
    """Convert a user-typed domain name to the ASCII form used on the wire.
    Raise ValueError for names that are not valid."""
    out = []
    for label in domain.split("."):
        if all(ord(c) < 128 for c in label):
            out.append(label.lower())
        else:
            out.append("xn--" + label.encode("punycode").decode("ascii"))
    return ".".join(out)
