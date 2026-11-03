import json, pathlib, pytest
from src.linebreak import break_opportunities

C = json.loads((pathlib.Path(__file__).parent.parent / "_hidden_tests" / "cases.json").read_text())


@pytest.mark.parametrize("text,expected", C, ids=[str(i) for i in range(len(C))])
def test_official(text, expected):
    assert break_opportunities(text) == expected


def test_no_banned_imports():
    import ast, pathlib
    banned = {'urllib', 'regex', 'pyphen', 'PyICU', 'requests', 'http', 'socket', 'icu', 'uniseg'}
    for f in pathlib.Path("src").rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            for n in names:
                assert n.split(".")[0] not in banned, (f, n)
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "__import__":
                raise AssertionError("dynamic import")
