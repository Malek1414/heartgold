"""Build the hard fixture suite. Hidden expected values come from real oracles, not from us:
packaging (PEP 440), croniter (cron), git itself (gitignore), protego (robots.txt, RFC 9309),
and the RFC 3986 section 5.4 examples (reference resolution).

Run once: .venv/bin/python bench/build_hard.py
"""
import datetime, json, pathlib, random, shutil, subprocess, tempfile, textwrap

ROOT = pathlib.Path(__file__).resolve().parent / "fixtures"
BAN_TEST = '''

def test_no_banned_imports():
    import ast, pathlib
    banned = {BANNED}
    for f in pathlib.Path("src").rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \\
                    [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            for n in names:
                assert n.split(".")[0] not in banned, (f, n)
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "__import__":
                raise AssertionError("dynamic import")
'''


def write(name, src, visible, goal, cases, hidden_body, banned):
    d = ROOT / name
    if d.exists():
        shutil.rmtree(d)
    (d / "repo" / "src").mkdir(parents=True)
    (d / "repo" / "tests").mkdir()
    (d / "hidden").mkdir()
    (d / "repo" / "src" / f"{name}.py").write_text(textwrap.dedent(src).lstrip())
    (d / "repo" / "tests" / f"test_{name}.py").write_text(textwrap.dedent(visible).lstrip())
    (d / "repo" / "goal.md").write_text(textwrap.dedent(goal).lstrip())
    (d / "hidden" / "cases.json").write_text(json.dumps(cases))
    body = textwrap.dedent(hidden_body).lstrip() + BAN_TEST.replace("{BANNED}", repr(set(banned)))
    (d / "hidden" / f"test_hidden_{name}.py").write_text(body)
    (d / "meta.json").write_text(json.dumps({"suite": "hard", "cases": len(cases)}))
    n = sum(len(v) for v in cases.values()) if isinstance(cases, dict) else len(cases)
    print(name, n, "cases")


# ---------------------------------------------------------------- pep440
def build_pep440():
    from packaging.version import InvalidVersion, Version
    rnd = random.Random(440)

    def rand_version():
        parts = []
        if rnd.random() < 0.15:
            parts.append(f"{rnd.randint(0, 3)}!")
        rel = ".".join(str(rnd.choice([0, 0, 1, 2, 10, 1, 3, 9, 11])) for _ in range(rnd.randint(1, 4)))
        if rnd.random() < 0.1:
            rel = rel.replace(".", ".0", 1) if "." in rel else "0" + rel
        parts.append(rel)
        if rnd.random() < 0.45:
            sep = rnd.choice(["", "", ".", "-", "_"])
            tag = rnd.choice(["a", "b", "rc", "alpha", "beta", "c", "pre", "preview", "A", "RC"])
            num = rnd.choice(["", "0", "1", "2", "10"])
            parts.append(f"{sep}{tag}{rnd.choice(['', '.', '-']) if num else ''}{num}")
        if rnd.random() < 0.3:
            parts.append(rnd.choice([".post1", "-post2", "post3", ".rev1", ".r2", "-1", ".post", "_post4", "-r"]))
        if rnd.random() < 0.3:
            parts.append(rnd.choice([".dev", ".dev0", ".dev3", "dev1", "-dev2", "_dev"]))
        if rnd.random() < 0.15:
            parts.append(rnd.choice(["+local", "+ubuntu-1", "+abc.5", "+1.2_3", "+Mixed.CASE"]))
        s = "".join(parts)
        if rnd.random() < 0.08:
            s = "v" + s
        if rnd.random() < 0.05:
            s = f"  {s}\t"
        return s

    valid, invalid = [], set()
    while len(valid) < 220:
        s = rand_version()
        try:
            valid.append((s, str(Version(s))))
        except InvalidVersion:
            invalid.add(s)
    invalid |= {"1.0.0-", "1..0", "a1.0", "1.0+", "1.0+local..1", "1.0.dev.post", "", "1.0-alpha_beta", "1.0+ab cd", "x"}
    invalid = sorted(i for i in invalid if not _valid(i))[:60]
    pairs = []
    for _ in range(400):
        (a, _), (b, _) = rnd.sample(valid, 2)
        va, vb = Version(a), Version(b)
        pairs.append([a, b, (va > vb) - (va < vb)])
    tricky = [("1.0", "1.0.0"), ("1.0.post1", "1.0"), ("1.0.dev1", "1.0a1"), ("1.0a1.dev1", "1.0a1"),
              ("1.0+abc", "1.0"), ("1.0+abc.5", "1.0+abc.10"), ("1.0+5", "1.0+abc"), ("1!0.1", "2.0"),
              ("1.0rc1", "1.0c1"), ("1.0.post1.dev1", "1.0.post1"), ("1.0.post1.dev1", "1.0"), ("1.0-1", "1.0.post1")]
    for a, b in tricky:
        va, vb = Version(a), Version(b)
        pairs.append([a, b, (va > vb) - (va < vb)])
    cases = dict(normalize=valid, invalid=invalid, compare=pairs)
    write("pep440", src='''
        """Version helper for our package index."""


        class InvalidVersion(ValueError):
            pass


        class Version:
            def __init__(self, text):
                try:
                    self.parts = tuple(int(p) for p in text.strip().split("."))
                except ValueError:
                    raise InvalidVersion(text)

            def __str__(self):
                return ".".join(map(str, self.parts))

            def _key(self):
                return self.parts

            def __eq__(self, other):
                return self._key() == other._key()

            def __lt__(self, other):
                return self._key() < other._key()

            def __le__(self, other):
                return self._key() <= other._key()

            def __gt__(self, other):
                return self._key() > other._key()

            def __ge__(self, other):
                return self._key() >= other._key()

            def __hash__(self):
                return hash(self._key())
        ''', visible='''
        from src.pep440 import Version


        def test_simple_order():
            assert Version("1.2") < Version("1.10")
            assert str(Version("2.0.1")) == "2.0.1"
        ''', goal='''
        Our package index must order and display versions exactly the way pip does:
        implement full PEP 440 ("Version Identification and Dependency Specification")
        parsing, normalization (`str(Version(s))` returns the normalized form) and
        ordering, including epochs, pre-, post- and dev-releases, local versions and all
        the alternative spellings PEP 440 says to accept. Invalid versions raise
        `InvalidVersion`. Equal versions must hash equal. Pure Python standard library
        only: `packaging` and other third-party modules are not available in production.
        Keep `Version` and `InvalidVersion` in `src/pep440.py`.
        ''', cases=cases, hidden_body='''
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
        ''', banned={"packaging", "pkg_resources", "setuptools", "pip", "distutils"})


def _valid(s):
    from packaging.version import InvalidVersion, Version
    try:
        Version(s)
        return True
    except InvalidVersion:
        return False


# ---------------------------------------------------------------- cron
def build_cron():
    from croniter import croniter
    rnd = random.Random(5)
    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]

    def field(lo, hi, names=None):
        r = rnd.random()
        if r < 0.3:
            return "*"
        if r < 0.45:
            return f"*/{rnd.choice([2, 3, 5, 7, 10, 15])}"
        if r < 0.6:
            a = rnd.randint(lo, hi - 1)
            b = rnd.randint(a, hi)
            step = rnd.choice(["", "", f"/{rnd.randint(2, 4)}"])
            return f"{a}-{b}{step}"
        if r < 0.75:
            return ",".join(str(x) for x in sorted(rnd.sample(range(lo, hi + 1), rnd.randint(2, 3))))
        if names and r < 0.85:
            return rnd.choice(names) if rnd.random() < 0.6 else f"{rnd.choice(names[:3])}-{rnd.choice(names[4:])}"
        return str(rnd.randint(lo, hi))

    cases = []
    while len(cases) < 260:
        dow = field(0, 7, days)
        expr = f"{field(0, 59)} {field(0, 23)} {field(1, 28)} {field(1, 12, months)} {dow}"
        after = datetime.datetime(2026, 1, 1) + datetime.timedelta(minutes=rnd.randint(0, 600000), seconds=rnd.choice([0, 0, 30]))
        try:
            it = croniter(expr, after)
            nxt = [it.get_next(datetime.datetime).isoformat() for _ in range(3)]
        except Exception:
            continue
        cases.append([expr, after.isoformat(), nxt])
    for expr in ["0 0 13 * FRI", "30 9 1,15 * MON", "0 12 * * 7", "0 0 29 2 *", "59 23 31 * *", "0 0 * * 0,7", "15 10 L * *"]:
        after = datetime.datetime(2026, 1, 1, 0, 0)
        try:
            it = croniter(expr, after)
            cases.append([expr, after.isoformat(), [it.get_next(datetime.datetime).isoformat() for _ in range(3)]])
        except Exception:
            pass
    cases = [c for c in cases if " L " not in f" {c[0]} "]
    write("cron", src='''
        """Scheduler: when does a cron job run next?"""
        import datetime


        def next_run(expr, after):
            """Return the first datetime strictly after `after` matching the 5-field cron `expr`."""
            minute, hour, dom, month, dow = expr.split()
            t = after.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
            for _ in range(60 * 24 * 366):
                if ((minute == "*" or t.minute == int(minute)) and (hour == "*" or t.hour == int(hour))
                        and (dom == "*" or t.day == int(dom)) and (month == "*" or t.month == int(month))
                        and (dow == "*" or t.isoweekday() % 7 == int(dow))):
                    return t
                t += datetime.timedelta(minutes=1)
            raise ValueError("no match within a year")
        ''', visible='''
        import datetime
        from src.cron import next_run


        def test_daily():
            assert next_run("30 2 * * *", datetime.datetime(2026, 3, 1, 5, 0)) == datetime.datetime(2026, 3, 2, 2, 30)
        ''', goal='''
        `next_run(expr, after)` must behave exactly like standard (Vixie) cron for the
        5-field syntax used in crontab(5): lists, ranges, steps on ranges and on `*`,
        month and day-of-week names (case-insensitive), both 0 and 7 meaning Sunday, and
        the crontab rule for how day-of-month and day-of-week combine. Return the first
        matching minute strictly after `after` (naive datetimes, seconds zero). It must
        also be fast for sparse schedules (e.g. Feb 29 only). Standard library only (no
        croniter).
        ''', cases=cases, hidden_body='''
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
        ''', banned={"croniter", "crontab", "apscheduler", "cron_descriptor"})


# ---------------------------------------------------------------- gitignore
def build_gitignore():
    rnd = random.Random(9)
    names = ["build", "src", "lib", "a", "b", "doc", "logs", "node_modules", "Foo", "x.log", "y.txt", "cache"]
    pats_pool = ["*.log", "build/", "/build", "build", "doc/*.txt", "**/logs", "logs/**", "a/**/b", "!x.log",
                 "!important.log", "*.txt", "!/src/keep.txt", "\\!bang", "\\#hash", "#comment", "foo/", "Foo",
                 "cache/*", "!cache/keep", "*.py[co]", "file?.txt", "[ab].md", "lib/*/z", "/*.md", "trail   ",
                 "trail\\ ", "**/node_modules/", "src/**/*.log", "*/", "!lib/", "a/b", "deep/**/", "!*/"]
    files_pool = ["x.log", "app.log", "build/out.o", "src/build/obj.o", "build", "doc/a.txt", "doc/sub/b.txt",
                  "logs/today", "src/logs/1", "a/b", "a/x/b", "a/x/y/b", "!bang", "#hash", "foo/bar", "Foo/q",
                  "cache/keep", "cache/tmp", "m.pyc", "n.pyo", "file1.txt", "file10.txt", "a.md", "c.md",
                  "doc/r.md", "lib/k/z", "lib/k/l/z", "trail", "trail ", "node_modules/p/i.js", "src/node_modules/q",
                  "src/a/b/c.log", "src/keep.txt", "y.txt", "deep/k/f", "important.log", "lib/q.c", "z/y/x"]
    cases = []
    with tempfile.TemporaryDirectory() as td:
        for _ in range(90):
            pats = rnd.sample(pats_pool, rnd.randint(2, 6))
            files = sorted(set(rnd.sample(files_pool, rnd.randint(8, 16))))
            files = [f for f in files if not any(g != f and g.startswith(f + "/") for g in files)
                     and not any(f.startswith(g + "/") for g in files)]
            low = {}
            for f in files:
                for i in range(1, f.count("/") + 2):
                    k = "/".join(f.split("/")[:i])
                    low.setdefault(k.lower(), set()).add(k)
            if any(len(v) > 1 for v in low.values()):
                continue
            repo = pathlib.Path(td) / f"r{len(cases)}"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "core.ignorecase", "false"], cwd=repo, check=True)
            for f in files:
                p = repo / f
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("x")
            (repo / ".gitignore").write_text("\n".join(pats) + "\n")
            out = subprocess.run(["git", "ls-files", "--others", "--ignored", "--exclude-standard", "-z"],
                                 cwd=repo, capture_output=True, text=True, check=True).stdout
            ignored = sorted(x for x in out.split("\0") if x and x != ".gitignore")
            cases.append([pats, files, ignored])
    write("gitignore", src='''
        """Decide which files our sync tool skips, using .gitignore rules."""
        import fnmatch


        def ignored(patterns, paths):
            """Return the subset of file `paths` (relative, '/'-separated) that the
            .gitignore lines `patterns` exclude."""
            out = set()
            for path in paths:
                name = path.split("/")[-1]
                for p in patterns:
                    p = p.strip()
                    if not p or p.startswith("#"):
                        continue
                    if fnmatch.fnmatch(name, p) or fnmatch.fnmatch(path, p):
                        out.add(path)
            return out
        ''', visible='''
        from src.gitignore import ignored


        def test_extension():
            assert ignored(["*.log"], ["a.log", "b.txt"]) == {"a.log"}
        ''', goal='''
        `ignored(patterns, paths)` must return exactly the files git itself would treat
        as ignored for a root `.gitignore` containing `patterns` (one line each) - same
        semantics as gitignore(5): negation, directory-only patterns, anchoring,
        `**`, character classes, escaping, trailing spaces, comments, and the rule about
        files inside excluded directories. `paths` are files relative to the repo root.
        Do not shell out to git, and do not use the pathspec library.
        ''', cases=cases, hidden_body='''
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
        ''', banned={"pathspec", "subprocess", "gitignore_parser", "igittigitt"})


# ---------------------------------------------------------------- robots (RFC 9309)
def build_robots():
    from protego import Protego
    rnd = random.Random(93)
    agents = ["FooBot", "foobot/2.1", "BarBot", "Googlebot", "*"]
    paths = ["/", "/private", "/private/", "/private/x", "/public/a.html", "/a.php", "/a.php?x=1", "/fish",
             "/fish.html", "/fish/salmon", "/Fish", "/catfish", "/page.PHP", "/x/y/z", "/%7Ejoe/", "/~joe/",
             "/a%2fb", "/search?q=1", "/$", "/index.html", "/tmp/", "/tmp", "/en/docs/", "/images/a.jpg"]
    rules = ["Disallow: /private", "Allow: /private/x", "Disallow: /fish", "Allow: /fish.html", "Disallow: /*.php$",
             "Disallow: /*.php", "Allow: /$", "Disallow: /", "Disallow:", "Allow: /public/", "Disallow: /*?",
             "Disallow: /~joe/", "Disallow: /%7ejoe/", "Disallow: /tmp/", "Allow: /tmp/$", "Disallow: /x/*/z",
             "Disallow: /images/*.jpg", "Allow: /en/", "Disallow: /*/docs/", "disallow: /search", "DISALLOW: /index"]
    cases = []
    for _ in range(80):
        groups = []
        for _ in range(rnd.randint(1, 3)):
            uas = rnd.sample(["FooBot", "barbot", "*", "Googlebot", "foobot"], rnd.randint(1, 2))
            lines = [f"User-agent: {u}" for u in uas] + rnd.sample(rules, rnd.randint(1, 5))
            groups.append("\n".join(lines))
        extras = rnd.choice(["", "Sitemap: https://x.test/s.xml\n", "# comment\n", "Crawl-delay: 5\n"])
        txt = extras + "\n\n".join(groups) + "\n"
        if rnd.random() < 0.2:
            txt = txt.replace("\n", "\r\n")
        rp = Protego.parse(txt)
        for _ in range(8):
            a, p = rnd.choice(agents), rnd.choice(paths)
            cases.append([txt, a, p, bool(rp.can_fetch("https://x.test" + p, a))])
    write("robots", src='''
        """robots.txt checker for our crawler."""


        def can_fetch(robots_txt, user_agent, path):
            """May `user_agent` crawl `path` (path + optional query) under `robots_txt`?"""
            applies = False
            for line in robots_txt.splitlines():
                key, _, value = line.partition(":")
                key, value = key.strip().lower(), value.strip()
                if key == "user-agent":
                    applies = value == "*" or value == user_agent
                elif applies and key == "disallow" and value and path.startswith(value):
                    return False
            return True
        ''', visible='''
        from src.robots import can_fetch


        def test_disallow_prefix():
            assert can_fetch("User-agent: *\\nDisallow: /private\\n", "Bot", "/private/x") is False
            assert can_fetch("User-agent: *\\nDisallow: /private\\n", "Bot", "/public") is True
        ''', goal='''
        Make `can_fetch` follow RFC 9309 (Robots Exclusion Protocol) the way Google's
        robots.txt parser does: user-agent group selection and merging (product token,
        case-insensitive, version suffix ignored, `*` fallback), most-specific (longest)
        match wins, Allow vs Disallow ties, `*` and `$` in patterns, empty Disallow,
        case-insensitive directives, CRLF, comments, unknown lines, and percent-encoding
        normalization when matching paths. Standard library only (no protego, no
        urllib.robotparser).
        ''', cases=cases, hidden_body='''
        import json, pathlib, pytest
        from src.robots import can_fetch

        C = json.loads((pathlib.Path(__file__).parent.parent / "_hidden_tests" / "cases.json").read_text())


        @pytest.mark.parametrize("txt,agent,path,expected", C)
        def test_case(txt, agent, path, expected):
            assert can_fetch(txt, agent, path) == expected
        ''', banned={"protego", "urllib", "reppy", "robotexclusionrulesparser"})


# ---------------------------------------------------------------- urljoin (RFC 3986 5.4)
def build_urljoin():
    base = "http://a/b/c/d;p?q"
    normal = {"g:h": "g:h", "g": "http://a/b/c/g", "./g": "http://a/b/c/g", "g/": "http://a/b/c/g/",
              "/g": "http://a/g", "//g": "http://g", "?y": "http://a/b/c/d;p?y", "g?y": "http://a/b/c/g?y",
              "#s": "http://a/b/c/d;p?q#s", "g#s": "http://a/b/c/g#s", "g?y#s": "http://a/b/c/g?y#s",
              ";x": "http://a/b/c/;x", "g;x": "http://a/b/c/g;x", "g;x?y#s": "http://a/b/c/g;x?y#s",
              "": "http://a/b/c/d;p?q", ".": "http://a/b/c/", "./": "http://a/b/c/", "..": "http://a/b/",
              "../": "http://a/b/", "../g": "http://a/b/g", "../..": "http://a/", "../../": "http://a/",
              "../../g": "http://a/g"}
    abnormal = {"../../../g": "http://a/g", "../../../../g": "http://a/g", "/./g": "http://a/g",
                "/../g": "http://a/g", "g.": "http://a/b/c/g.", ".g": "http://a/b/c/.g", "g..": "http://a/b/c/g..",
                "..g": "http://a/b/c/..g", "./../g": "http://a/b/g", "./g/.": "http://a/b/c/g/",
                "g/./h": "http://a/b/c/g/h", "g/../h": "http://a/b/c/h", "g;x=1/./y": "http://a/b/c/g;x=1/y",
                "g;x=1/../y": "http://a/b/c/y", "g?y/./x": "http://a/b/c/g?y/./x", "g?y/../x": "http://a/b/c/g?y/../x",
                "g#s/./x": "http://a/b/c/g#s/./x", "g#s/../x": "http://a/b/c/g#s/../x", "http:g": "http:g"}
    extra = [["http://a/b/c/d;p?q", "g?", "http://a/b/c/g?"], ["http://a/b/c/d;p?q", "#", "http://a/b/c/d;p?q#"],
             ["http://a", "g", "http://a/g"], ["http://a/b/", "../../../x/./y/../z", "http://a/x/z"],
             ["http://u@a:8080/b/c", "../d", "http://u@a:8080/d"], ["file:///etc/x", "y", "file:///etc/y"],
             ["http://a/b/c", "//other/p/../q", "http://other/q"], ["mailto:x@y", "#f", "mailto:x@y#f"],
             ["http://a/b/c/d;p?q", "g?y#", "http://a/b/c/g?y#"], ["HTTP://A/b", "c", "HTTP://A/c"]]
    cases = [[base, r, t] for r, t in normal.items()] + [[base, r, t] for r, t in abnormal.items()] + extra
    write("urljoin", src='''
        """Resolve links found on crawled pages."""


        def resolve(base, ref):
            """Resolve URI reference `ref` against absolute URI `base`."""
            if "://" in ref:
                return ref
            if ref.startswith("/"):
                scheme, rest = base.split("://", 1)
                return scheme + "://" + rest.split("/", 1)[0] + ref
            return base.rsplit("/", 1)[0] + "/" + ref
        ''', visible='''
        from src.urljoin import resolve


        def test_relative():
            assert resolve("http://a/b/c", "d") == "http://a/b/d"
        ''', goal='''
        `resolve(base, ref)` must implement URI reference resolution exactly as RFC 3986
        section 5 specifies (strict parser), including remove_dot_segments, empty
        references, query-only and fragment-only references, network-path references,
        and the "normal" and "abnormal" examples the RFC lists. Do not normalize case
        or percent-encoding beyond what section 5 requires. Standard library only, and
        do not use urllib.
        ''', cases=cases, hidden_body='''
        import json, pathlib, pytest
        from src.urljoin import resolve

        C = json.loads((pathlib.Path(__file__).parent.parent / "_hidden_tests" / "cases.json").read_text())


        @pytest.mark.parametrize("base,ref,expected", C)
        def test_resolve(base, ref, expected):
            assert resolve(base, ref) == expected
        ''', banned={"urllib", "requests", "yarl", "furl", "rfc3986", "httpx"})


if __name__ == "__main__":
    build_pep440()
    build_cron()
    build_gitignore()
    build_robots()
    build_urljoin()
