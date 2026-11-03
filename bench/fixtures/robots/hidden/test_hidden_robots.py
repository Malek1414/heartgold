import json, pathlib, pytest
from src.robots import can_fetch

C = json.loads((pathlib.Path(__file__).parent.parent / "_hidden_tests" / "cases.json").read_text())


@pytest.mark.parametrize("txt,agent,path,expected", C)
def test_case(txt, agent, path, expected):
    assert can_fetch(txt, agent, path) == expected


def test_no_banned_imports():
    import ast, pathlib
    banned = {'reppy', 'robotexclusionrulesparser', 'protego', 'urllib'}
    for f in pathlib.Path("src").rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            for n in names:
                assert n.split(".")[0] not in banned, (f, n)
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "__import__":
                raise AssertionError("dynamic import")
