"""Puzzle solver."""


def count_solutions(n):
    """Number of ways to place n non-attacking queens on an n x n board."""
    def ok(rows, col):
        r = len(rows)
        return all(c != col and abs(c - col) != r - i for i, c in enumerate(rows))

    def place(rows):
        if len(rows) == n:
            return 1
        return sum(place(rows + [c]) for c in range(n) if ok(rows, c))

    return place([])
