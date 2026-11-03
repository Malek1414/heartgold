import json, pathlib, pytest
from src.urljoin import resolve

C = json.loads((pathlib.Path(__file__).parent.parent / "_hidden_tests" / "cases.json").read_text())


@pytest.mark.parametrize("base,ref,expected", C)
def test_resolve(base, ref, expected):
    assert resolve(base, ref) == expected


def test_no_banned_imports():
    import ast, pathlib
    banned = {'requests', 'httpx', 'furl', 'urllib', 'rfc3986', 'yarl'}
    for f in pathlib.Path("src").rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            for n in names:
                assert n.split(".")[0] not in banned, (f, n)
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "__import__":
                raise AssertionError("dynamic import")
