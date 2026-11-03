import datetime, json, pathlib, pytest
from src.cron import next_run

C = json.loads((pathlib.Path(__file__).parent.parent / "_hidden_tests" / "cases.json").read_text())


@pytest.mark.parametrize("expr,after,expected", C)
def test_next_runs(expr, after, expected):
    t = datetime.datetime.fromisoformat(after)
    got = []
    for _ in range(3):
        t = next_run(expr, t)
        got.append(t.isoformat())
    assert got == expected


def test_sparse_is_fast():
    import time
    t0 = time.perf_counter()
    assert next_run("0 0 29 2 *", datetime.datetime(2026, 3, 1)) == datetime.datetime(2028, 2, 29)
    assert time.perf_counter() - t0 < 0.5


def test_no_banned_imports():
    import ast, pathlib
    banned = {'cron_descriptor', 'crontab', 'apscheduler', 'croniter'}
    for f in pathlib.Path("src").rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            for n in names:
                assert n.split(".")[0] not in banned, (f, n)
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "__import__":
                raise AssertionError("dynamic import")
