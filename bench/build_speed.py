"""Build the open-ended speed suite (suite "speed"). Score has no ceiling: any wrong hidden case zeroes
speed credit, and speed is measured on a HIDDEN benchmark with different inputs than the visible bench.py.

Run once: .venv/bin/python bench/build_speed.py
"""
import importlib.util, json, pathlib, random, shutil, sys, textwrap

ROOT = pathlib.Path(__file__).resolve().parent / "fixtures"


def load(path):
    spec = importlib.util.spec_from_file_location("m", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def write(name, src, goal, visible, bench, hidden_bench, make_cases, check_body):
    d = ROOT / name
    if d.exists():
        shutil.rmtree(d)
    (d / "repo" / "src").mkdir(parents=True)
    (d / "repo" / "tests").mkdir()
    (d / "hidden").mkdir()
    (d / "repo" / "src" / f"{name}.py").write_text(textwrap.dedent(src).lstrip())
    (d / "repo" / "goal.md").write_text(textwrap.dedent(goal).lstrip())
    (d / "repo" / "tests" / f"test_{name}.py").write_text(textwrap.dedent(visible).lstrip())
    (d / "repo" / "bench.py").write_text(textwrap.dedent(bench).lstrip())
    (d / "hidden" / "bench_hidden.py").write_text(textwrap.dedent(hidden_bench).lstrip())
    naive = load(d / "repo" / "src" / f"{name}.py")
    cases = make_cases(naive)
    (d / "hidden" / "cases.json").write_text(json.dumps(cases))
    (d / "hidden" / f"test_hidden_{name}.py").write_text(textwrap.dedent(check_body).lstrip())
    import subprocess, tempfile, time
    tmp = pathlib.Path(tempfile.mkdtemp())
    shutil.copytree(d / "repo", tmp, dirs_exist_ok=True)
    shutil.copy(d / "hidden" / "bench_hidden.py", tmp / "bench_hidden.py")
    t0 = time.time()
    out = subprocess.run([sys.executable, "bench_hidden.py"], cwd=tmp, capture_output=True, text=True, timeout=1800).stdout
    base = float(out.strip().splitlines()[-1])
    (d / "meta.json").write_text(json.dumps({"suite": "speed", "speed_mode": "open", "cases": len(cases),
                                              "base_hidden_time": base}))
    print(f"  naive hidden bench: {base:.2f}s (wall {time.time() - t0:.0f}s)")
    print(name, len(cases), "cases")


HIDDEN_HEAD = '''
import json, pathlib, pytest
C = json.loads((pathlib.Path(__file__).parent.parent / "_hidden_tests" / "cases.json").read_text())
'''


def build_lcs():
    def cases(m):
        rnd = random.Random(1)
        out = []
        for _ in range(120):
            alpha = rnd.choice(["ab", "acgt", "abcdefghij", "xyzé中"])
            a = "".join(rnd.choice(alpha) for _ in range(rnd.randint(0, 120)))
            b = "".join(rnd.choice(alpha) for _ in range(rnd.randint(0, 120)))
            out.append([a, b, m.lcs_length(a, b)])
        out += [["", "", 0], ["a", "", 0], ["abc", "abc", 3], ["a" * 70, "a" * 65, 65]]
        return out
    write("lcs", src='''
        """Diff engine core."""


        def lcs_length(a, b):
            """Length of the longest common subsequence of strings a and b."""
            n, m = len(a), len(b)
            table = [[0] * (m + 1) for _ in range(n + 1)]
            for i in range(1, n + 1):
                for j in range(1, m + 1):
                    if a[i - 1] == b[j - 1]:
                        table[i][j] = table[i - 1][j - 1] + 1
                    else:
                        table[i][j] = max(table[i - 1][j], table[i][j - 1])
            return table[n][m]
        ''', goal='''
        Make `lcs_length(a, b)` as fast as possible for long inputs (thousands of
        characters, any Unicode alphabet) without changing its results. Pure Python
        standard library only (no C extensions, no numpy). `bench.py` prints seconds;
        lower is better. Speed is the only goal; results must stay identical.
        ''', visible='''
        from src.lcs import lcs_length


        def test_small():
            assert lcs_length("ABCBDAB", "BDCABA") == 4
        ''', bench='''
        import random, time
        from src.lcs import lcs_length
        rnd = random.Random(7)
        a = "".join(rnd.choice("acgt") for _ in range(2500))
        b = "".join(rnd.choice("acgt") for _ in range(2500))
        t = time.perf_counter(); lcs_length(a, b); print(time.perf_counter() - t)
        ''', hidden_bench='''
        import random, time
        from src.lcs import lcs_length
        rnd = random.Random(99)
        pairs = [("".join(rnd.choice(al) for _ in range(n)), "".join(rnd.choice(al) for _ in range(m)))
                 for al, n, m in [("abcdefghijklmnopqrstuvwxyz", 2200, 2400), ("01", 2600, 2000), ("acgté", 1800, 2300)]]
        t = time.perf_counter()
        for a, b in pairs:
            lcs_length(a, b)
        print(time.perf_counter() - t)
        ''', make_cases=cases, check_body=HIDDEN_HEAD + '''
        from src.lcs import lcs_length


        @pytest.mark.parametrize("a,b,expected", C)
        def test_same_result(a, b, expected):
            assert lcs_length(a, b) == expected
        ''')


def build_primes():
    def cases(m):
        vals = [0, 1, 2, 3, 4, 10, 11, 100, 997, 1000, 7919, 65536, 100000, 999983, 1000000]
        rnd = random.Random(3)
        vals += [rnd.randint(0, 300000) for _ in range(25)]
        return [[v, m.count_primes(v)] for v in vals]
    write("primes", src='''
        """Number theory helpers."""


        def count_primes(n):
            """Number of primes p with p <= n."""
            count = 0
            for k in range(2, n + 1):
                d = 2
                is_prime = True
                while d * d <= k:
                    if k % d == 0:
                        is_prime = False
                        break
                    d += 1
                if is_prime:
                    count += 1
            return count
        ''', goal='''
        Make `count_primes(n)` as fast as possible for large n (up to 10**8) without
        changing its results. Pure Python standard library only (no C extensions, no
        numpy, no precomputed tables of answers). `bench.py` prints seconds; lower is
        better. Speed is the only goal; results must stay identical.
        ''', visible='''
        from src.primes import count_primes


        def test_small():
            assert count_primes(30) == 10
        ''', bench='''
        import time
        from src.primes import count_primes
        t = time.perf_counter(); count_primes(300000); print(time.perf_counter() - t)
        ''', hidden_bench='''
        import time
        from src.primes import count_primes
        t = time.perf_counter()
        for n in (2_000_003, 1_234_567, 3_000_017):
            count_primes(n)
        print(time.perf_counter() - t)
        ''', make_cases=cases, check_body=HIDDEN_HEAD + '''
        from src.primes import count_primes


        @pytest.mark.parametrize("n,expected", C)
        def test_same_result(n, expected):
            assert count_primes(n) == expected


        def test_big_known():
            assert count_primes(10_000_000) == 664579
        ''')


def build_fuzzymatch():
    def cases(m):
        rnd = random.Random(5)
        words = sorted({"".join(rnd.choice("abcdeé") for _ in range(rnd.randint(1, 9))) for _ in range(400)})
        out = []
        for _ in range(40):
            q = "".join(rnd.choice("abcdeé") for _ in range(rnd.randint(0, 8)))
            k = rnd.randint(0, 3)
            out.append([q, words, k, m.within(q, words, k)])
        return out
    write("fuzzymatch", src='''
        """Spell-check candidates."""


        def _dist(a, b):
            prev = list(range(len(b) + 1))
            for i, ca in enumerate(a, 1):
                cur = [i]
                for j, cb in enumerate(b, 1):
                    cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
                prev = cur
            return prev[-1]


        def within(query, words, k):
            """All words whose Levenshtein distance to query is <= k, as (distance, word)
            pairs sorted by distance then word."""
            out = [(_dist(query, w), w) for w in words]
            return sorted((d, w) for d, w in out if d <= k)
        ''', goal='''
        Make `within(query, words, k)` as fast as possible for large word lists
        (100k+ words, small k) without changing its results. Pure Python standard
        library only (no C extensions). Each call may get a different word list, so
        do not rely on caching between calls. `bench.py` prints seconds; lower is
        better. Speed is the only goal; results must stay identical.
        ''', visible='''
        from src.fuzzymatch import within


        def test_small():
            assert within("cat", ["bat", "cart", "dog", "cat"], 1) == [(0, "cat"), (1, "bat"), (1, "cart")]
        ''', bench='''
        import random, string, time
        from src.fuzzymatch import within
        rnd = random.Random(2)
        words = ["".join(rnd.choice(string.ascii_lowercase) for _ in range(rnd.randint(4, 11))) for _ in range(30000)]
        t = time.perf_counter()
        for q in ("example", "zebra", "kitchen"):
            within(q, words, 2)
        print(time.perf_counter() - t)
        ''', hidden_bench='''
        import random, string, time
        from src.fuzzymatch import within
        rnd = random.Random(77)
        words = ["".join(rnd.choice("etaoinshrdlu") for _ in range(rnd.randint(3, 13))) for _ in range(60000)]
        t = time.perf_counter()
        for q, k in (("relations", 2), ("hound", 1), ("tradition", 3)):
            within(q, list(words), k)
        print(time.perf_counter() - t)
        ''', make_cases=cases, check_body=HIDDEN_HEAD + '''
        from src.fuzzymatch import within


        @pytest.mark.parametrize("q,words,k,expected", C)
        def test_same_result(q, words, k, expected):
            assert [list(x) for x in within(q, words, k)] == expected
        ''')


def build_nqueens():
    def cases(m):
        return [[n, m.count_solutions(n)] for n in range(0, 10)]
    write("nqueens", src='''
        """Puzzle solver."""


        def count_solutions(n):
            """Number of ways to place n non-attacking queens on an n x n board."""
            def ok(rows, col):
                r = len(rows)
                return all(c != col and abs(c - col) != r - i for i, c in enumerate(rows))

            def place(rows):
                if len(rows) == n:
                    return 1
                return sum(place(rows + [c]) for c in range(n) if ok(rows, c))

            return place([])
        ''', goal='''
        Make `count_solutions(n)` as fast as possible (n up to 14) without changing its
        results. Pure Python standard library only (no C extensions, and no hard-coded
        tables of answers). `bench.py` prints seconds; lower is better. Speed is the
        only goal; results must stay identical.
        ''', visible='''
        from src.nqueens import count_solutions


        def test_small():
            assert count_solutions(6) == 4
        ''', bench='''
        import time
        from src.nqueens import count_solutions
        t = time.perf_counter(); count_solutions(9); print(time.perf_counter() - t)
        ''', hidden_bench='''
        import time
        from src.nqueens import count_solutions
        t = time.perf_counter()
        assert count_solutions(10) == 724
        assert count_solutions(11) == 2680
        print(time.perf_counter() - t)
        ''', make_cases=cases, check_body=HIDDEN_HEAD + '''
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
        ''')


if __name__ == "__main__":
    for name in sys.argv[1:] or ["lcs", "primes", "fuzzymatch", "nqueens"]:
        globals()[f"build_{name}"]()
