import json, pathlib, pytest
from src.idna import to_ascii

C = json.loads((pathlib.Path(__file__).parent.parent / "_hidden_tests" / "cases.json").read_text())


@pytest.mark.parametrize("domain,expected", C, ids=[str(i) for i in range(len(C))])
def test_case(domain, expected):
    if expected is None:
        with pytest.raises(ValueError):
            to_ascii(domain)
    else:
        assert to_ascii(domain) == expected


def test_no_banned_imports():
    import ast, pathlib
    banned = {'urllib', 'http', 'socket', 'uts46', 'idna', 'encodings', 'requests'}
    for f in pathlib.Path("src").rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            for n in names:
                assert n.split(".")[0] not in banned, (f, n)
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "__import__":
                raise AssertionError("dynamic import")
