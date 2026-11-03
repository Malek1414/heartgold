import json, pathlib, pytest
C = json.loads((pathlib.Path(__file__).parent.parent / "_hidden_tests" / "cases.json").read_text())


import ast, pathlib as _p
from src.nqueens import count_solutions


@pytest.mark.parametrize("n,expected", C)
def test_same_result(n, expected):
    assert count_solutions(n) == expected


def test_larger():
    assert count_solutions(12) == 14200


def test_no_answer_table():
    # a table of the known counts (e.g. 14200, 73712) must not appear in the source
    src = "".join(f.read_text() for f in _p.Path("src").rglob("*.py"))
    nums = {n.value for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Constant) and isinstance(n.value, int)}
    assert not ({2680, 14200, 73712, 365596} & nums)
