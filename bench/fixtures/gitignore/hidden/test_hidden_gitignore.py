import json, pathlib, pytest
from src.gitignore import ignored

C = json.loads((pathlib.Path(__file__).parent.parent / "_hidden_tests" / "cases.json").read_text())


def _cases():
    for i, (pats, files, ign) in enumerate(C):
        for f in files:
            yield pytest.param(pats, files, f, f in ign, id=f"c{i}-{f}")


@pytest.mark.parametrize("pats,files,f,expected", list(_cases()))
def test_file(pats, files, f, expected):
    assert (f in set(ignored(pats, files))) == expected


def test_no_banned_imports():
    import ast, pathlib
    banned = {'subprocess', 'pathspec', 'gitignore_parser', 'igittigitt'}
    for f in pathlib.Path("src").rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            for n in names:
                assert n.split(".")[0] not in banned, (f, n)
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "__import__":
                raise AssertionError("dynamic import")
