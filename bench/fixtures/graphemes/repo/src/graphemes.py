"""Text utilities for our terminal UI."""
import unicodedata


def graphemes(text):
    """Split text into user-perceived characters."""
    out = []
    for ch in text:
        if out and unicodedata.combining(ch):
            out[-1] += ch
        else:
            out.append(ch)
    return out
