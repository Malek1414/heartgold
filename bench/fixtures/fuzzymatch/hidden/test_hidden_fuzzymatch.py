import json, pathlib, pytest
C = json.loads((pathlib.Path(__file__).parent.parent / "_hidden_tests" / "cases.json").read_text())

        from src.fuzzymatch import within


        @pytest.mark.parametrize("q,words,k,expected", C)
        def test_same_result(q, words, k, expected):
            assert [list(x) for x in within(q, words, k)] == expected
