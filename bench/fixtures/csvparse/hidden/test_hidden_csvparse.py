import ast, pathlib
from src.csvparse import parse


def test_comma_inside_quotes():
    assert parse('a,"b,c",d\r\n') == [["a", "b,c", "d"]]


def test_crlf_line_endings():
    assert parse("a,b\r\nc,d\r\n") == [["a", "b"], ["c", "d"]]


def test_newline_inside_quotes():
    assert parse('"x\r\ny",z\r\n') == [["x\r\ny", "z"]]


def test_escaped_double_quote():
    assert parse('"say ""hi""",b\r\n') == [['say "hi"', "b"]]


def test_last_record_without_line_break():
    assert parse("a,b\r\nc,d") == [["a", "b"], ["c", "d"]]


def test_empty_fields_kept():
    assert parse("a,,c\r\n,,\r\n") == [["a", "", "c"], ["", "", ""]]


def test_spaces_are_part_of_field():
    assert parse(" a , b \r\n") == [[" a ", " b "]]


def test_empty_quoted_field():
    assert parse('"",x\r\n') == [["", "x"]]


def test_no_csv_import():
    src = pathlib.Path("src/csvparse.py").read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(a.name != "csv" for a in node.names)
        if isinstance(node, ast.ImportFrom):
            assert node.module != "csv"
