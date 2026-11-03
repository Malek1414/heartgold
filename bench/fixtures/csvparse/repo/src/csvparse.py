"""Minimal CSV reader (no stdlib csv module allowed: this runs on a tiny embedded runtime)."""


def parse(text):
    """Parse CSV text into a list of rows (lists of strings)."""
    rows = []
    for line in text.split("\n"):
        if line == "":
            continue
        rows.append([field.strip('"') for field in line.split(",")])
    return rows
