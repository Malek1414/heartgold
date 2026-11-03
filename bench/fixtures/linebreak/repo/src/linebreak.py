"""Word-wrap helper."""


def break_opportunities(text):
    """Return the indices i (1..len(text)) where a line break is allowed before text[i]
    (len(text) = after the last character)."""
    out = [i + 1 for i, ch in enumerate(text) if ch == " "]
    if text and (not out or out[-1] != len(text)):
        out.append(len(text))
    return out
