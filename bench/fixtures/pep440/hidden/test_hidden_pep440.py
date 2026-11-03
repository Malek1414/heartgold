import json, pathlib, pytest
from src.pep440 import InvalidVersion, Version

C = json.loads((pathlib.Path(__file__).parent.parent / "_hidden_tests" / "cases.json").read_text())


@pytest.mark.parametrize("raw,norm", C["normalize"])
def test_normalize(raw, norm):
    assert str(Version(raw)) == norm


@pytest.mark.parametrize("raw", C["invalid"])
def test_invalid(raw):
    with pytest.raises(InvalidVersion):
        Version(raw)


@pytest.mark.parametrize("a,b,sign", C["compare"])
def test_compare(a, b, sign):
    va, vb = Version(a), Version(b)
    assert ((va > vb) - (va < vb)) == sign
    assert (va == vb) == (sign == 0)
    if sign == 0:
        assert hash(va) == hash(vb)


def test_no_banned_imports():
    import ast, pathlib
    banned = {'distutils', 'pkg_resources', 'setuptools', 'pip', 'packaging'}
    for f in pathlib.Path("src").rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            for n in names:
                assert n.split(".")[0] not in banned, (f, n)
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "__import__":
                raise AssertionError("dynamic import")
