import json, pathlib, pytest
C = json.loads((pathlib.Path(__file__).parent.parent / "_hidden_tests" / "cases.json").read_text())

        from src.lcs import lcs_length


        @pytest.mark.parametrize("a,b,expected", C)
        def test_same_result(a, b, expected):
            assert lcs_length(a, b) == expected
