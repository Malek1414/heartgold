import json, pathlib, pytest
from src.graphemes import graphemes

C = json.loads((pathlib.Path(__file__).parent.parent / "_hidden_tests" / "cases.json").read_text())


@pytest.mark.parametrize("text,expected", C, ids=[" ".join(f"{ord(c):04X}" for c in t) for t, _ in C])
def test_official(text, expected):
    assert graphemes(text) == expected


def test_no_banned_imports():
    import ast, pathlib
    banned = {'urllib', 'grapheme', 'regex', 'PyICU', 'requests', 'http', 'socket', 'icu', 'uniseg'}
    for f in pathlib.Path("src").rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            for n in names:
                assert n.split(".")[0] not in banned, (f, n)
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "__import__":
                raise AssertionError("dynamic import")
