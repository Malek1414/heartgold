"""Version helper for our package index."""


class InvalidVersion(ValueError):
    pass


class Version:
    def __init__(self, text):
        try:
            self.parts = tuple(int(p) for p in text.strip().split("."))
        except ValueError:
            raise InvalidVersion(text)

    def __str__(self):
        return ".".join(map(str, self.parts))

    def _key(self):
        return self.parts

    def __eq__(self, other):
        return self._key() == other._key()

    def __lt__(self, other):
        return self._key() < other._key()

    def __le__(self, other):
        return self._key() <= other._key()

    def __gt__(self, other):
        return self._key() > other._key()

    def __ge__(self, other):
        return self._key() >= other._key()

    def __hash__(self):
        return hash(self._key())
