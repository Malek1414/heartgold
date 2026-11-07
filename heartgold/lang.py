# Copyright 2026 Malek Hassan (https://github.com/Malek1414/heartgold)
# SPDX-License-Identifier: Apache-2.0
"""Languages heartgold can work in: how to run a repo's tests, read their results, place heartgold's own tests,
and run a probe program, for each ecosystem.

Everything language-specific lives here; the pipeline in core.py talks to a Lang. heartgold writes three test
files of its own (spec, diff, adv). Each language either runs one file by path (pytest, the JS runners, rspec,
phpunit) or selects tests by name (cargo, go, maven, swift, dotnet, ctest), so heartgold's tests carry a name
prefix per kind (heartgold_spec_..., HeartgoldSpec...) and the repo's own tests are "everything else".

The probe protocol is the same in every language: a program that calls the public API on many inputs and prints,
on its last line, one JSON array with one string per case: "=" + the result as canonical JSON, or "!" + the error
type. heartgold records it against the original code and compares every candidate with it.
"""
from __future__ import annotations

import json, pathlib, re, shlex, sys
from dataclasses import dataclass, field

KINDS = ("spec", "diff", "adv")


@dataclass(frozen=True)
class Lang:
    name: str
    framework: str                      # for prompts: what the tests are written with
    exts: tuple                          # source file extensions
    test_cmd: str                        # the whole suite
    test_path: str                       # where heartgold's test of {kind} goes ({kind}, {Kind} filled in)
    select: str                          # "path": run a file by appending its path; else a command with {name}
    skip_ours: str = ""                  # the repo's own tests only (everything without our prefix); "" = run all
    probe_path: str = ""                 # where the probe program goes in a worktree
    probe_cmd: str = ""                  # how to run it
    bench_files: tuple = ()
    bench_cmd: str = ""                  # {file} filled in
    test_name_hint: str = ""             # how to name heartgold's tests so `select` finds them
    markers: tuple = field(default=())   # files at the repo root that identify the language

    def name_of(self, kind: str) -> str:
        return {"py": f"heartgold_{kind}", "camel": f"Heartgold{kind.capitalize()}"}[
            "camel" if self.name in ("java", "swift", "dotnet", "go") else "py"]

    def naming(self, kind: str) -> str:
        """What heartgold's tests of this kind must be called so they can be run on their own, for prompts."""
        n = self.name_of(kind)
        return {
            "python": f"put them in {self.path_of(kind)}",
            "js": f"put them in {self.path_of(kind)} (an ES module the repo's runner picks up)",
            "rust": f"put them in {self.path_of(kind)}; it is its own integration-test crate named {n}",
            "go": f"put them in {self.path_of(kind)} in the package under test; name every test function Test{n}<What>",
            "java": f"one class {n}Test in {self.path_of(kind)}",
            "ruby": f"put them in {self.path_of(kind)}",
            "swift": f"one XCTestCase class {n}Tests in the package's test target (add the target to Package.swift if there is none)",
            "dotnet": f"one test class {n}Tests in the solution's test project",
            "cpp": f"one executable from {self.path_of(kind)}, registered with add_test(NAME {n} ...) in CMakeLists.txt",
            "php": f"one class {n}Test in {self.path_of(kind)}",
        }[self.name]

    def probe_rule(self) -> str:
        """How the probe program is built and run, for prompts. Empty when the language has no probe."""
        if self.name == "python" or not self.probe_cmd:
            return ""
        extra = {"cpp": " and add an executable target heartgold_probe for it in CMakeLists.txt",
                 "go": " (package main)", "java": " (a class HeartgoldProbe with a main method)",
                 "rust": " (a cargo example: it can use the crate by name)"}.get(self.name, "")
        return (f"Write the probe as a program at {self.probe_path}{extra}, run with `{self.probe_cmd}`. It calls the "
                "public API on each case and prints, on its LAST line, one JSON array with one string per case: "
                '"=" followed by the result as JSON, or "!" followed by the error type if the call fails.')

    def path_of(self, kind: str) -> str:
        if self.name == "python" and kind == "adv":
            return "tests/test_heartgold_adversarial.py"  # the name heartgold always used for Python
        return self.test_path.format(kind=kind, Kind=kind.capitalize())

    def bench_slot(self, name: str) -> tuple[str, str] | None:
        """Where an extra benchmark program called `name` goes in a worktree, and how to run it (prints seconds on
        its last line). None: this language has no slot yet, so only the repo's own benchmark is used."""
        cls = "".join(w.capitalize() for w in name.strip("_").split("_"))
        return {
            "python": (f"{name}.py", f"{sys.executable} {name}.py"),
            "js": (f"{name}.mjs", f"node {name}.mjs"),
            "rust": (f"examples/{name}.rs", f"cargo run -q --release --example {name}"),
            # Go skips directories that start with "_" or "."
            "go": (f"cmd/heartgold{name}/main.go", f"go run ./cmd/heartgold{name}"),
            "ruby": (f"{name}.rb", f"ruby -I lib {name}.rb"),
            "php": (f"{name}.php", f"php {name}.php"),
            "java": (f"src/main/java/{cls}.java", f"mvn -q -B compile && java -cp target/classes {cls}"),
        }.get(self.name)

    @property
    def label(self) -> str:
        return {"js": "JavaScript/TypeScript", "cpp": "C/C++", "dotnet": "C#", "php": "PHP"}.get(self.name, self.name.capitalize())

    def run_kind(self, kind: str) -> str:
        """Command that runs only heartgold's tests of this kind."""
        if self.select == "path":
            return f"{self.test_cmd} {shlex.quote(self.path_of(kind))}"
        return self.select.format(name=self.name_of(kind), test_cmd=self.test_cmd)

    def run_orig(self, orig_paths: list) -> str:
        if self.select == "path":
            return f"{self.test_cmd} " + " ".join(map(shlex.quote, orig_paths)) if orig_paths else self.test_cmd
        return self.skip_ours.format(test_cmd=self.test_cmd) if self.skip_ours else self.test_cmd

    def is_test_file(self, rel: str) -> bool:
        return bool(re.search(r"(^|/)(tests?|spec|__tests__|src/test)/|(^|/)test_|_test\.|\.test\.|\.spec\.|_spec\.rb$|Tests?\.(java|swift|cs|kt)$", rel))


def _py_cmd():
    import importlib.util
    extra = " --timeout=60" if importlib.util.find_spec("pytest_timeout") else ""
    return f"{sys.executable} -m pytest -q -p no:cacheprovider{extra}"


def _js_cmd(repo: pathlib.Path) -> str:
    try:
        pkg = json.loads((repo / "package.json").read_text())
    except Exception:
        pkg = {}
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    if "vitest" in deps:
        return "npx vitest run"
    if "jest" in deps:
        return "npx jest"
    return "node --test"


LANGS: dict[str, Lang] = {
    "python": Lang("python", "pytest", (".py",), "", "tests/test_heartgold_{kind}.py", "path",
                   probe_path=".heartgold_probe.json", bench_files=("bench.py",), bench_cmd=f"{sys.executable} {{file}}",
                   markers=("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt")),
    "js": Lang("js", "the repo's JavaScript/TypeScript test runner", (".js", ".mjs", ".cjs", ".ts", ".tsx"), "",
               "tests/heartgold_{kind}.test.mjs", "path", probe_path=".heartgold_probe.mjs", probe_cmd="node .heartgold_probe.mjs",
               bench_files=("bench.mjs", "bench.js"), bench_cmd="node {file}", markers=("package.json",)),
    "rust": Lang("rust", "Rust #[test] functions in an integration test (tests/*.rs)", (".rs",), "cargo test -q",
                 "tests/heartgold_{kind}.rs", "cargo test -q --test {name}",
                 skip_ours="{test_cmd} -- --skip heartgold_",
                 probe_path="examples/heartgold_probe.rs", probe_cmd="cargo run -q --release --example heartgold_probe",
                 bench_files=("examples/bench.rs",), bench_cmd="cargo run -q --release --example bench", markers=("Cargo.toml",)),
    "go": Lang("go", "Go testing (func TestXxx(t *testing.T)) in a _test.go file of the package", (".go",), "go test -v ./...",
               "heartgold_{kind}_test.go", "go test -v ./... -run '^Test{name}'", skip_ours="{test_cmd} -skip '^TestHeartgold'",
               probe_path="cmd/heartgold_probe/main.go", probe_cmd="go run ./cmd/heartgold_probe",
               bench_files=("cmd/bench/main.go",), bench_cmd="go run ./cmd/bench", markers=("go.mod",)),
    "java": Lang("java", "JUnit 5 tests run by Maven", (".java",), "mvn -B -ntp test",
                 "src/test/java/Heartgold{Kind}Test.java", "mvn -B -ntp test -Dtest='{name}*' -Dsurefire.failIfNoSpecifiedTests=false",
                 skip_ours="{test_cmd} -Dtest='!Heartgold*' -Dsurefire.failIfNoSpecifiedTests=false",
                 probe_path="src/main/java/HeartgoldProbe.java",
                 probe_cmd="mvn -q -B compile && java -cp target/classes HeartgoldProbe", markers=("pom.xml",)),
    "ruby": Lang("ruby", "RSpec specs", (".rb",), "rspec", "spec/heartgold_{kind}_spec.rb", "path",
                 probe_path=".heartgold_probe.rb", probe_cmd="ruby -I lib .heartgold_probe.rb",
                 bench_files=("bench.rb",), bench_cmd="ruby -I lib {file}", markers=("Gemfile", ".rspec")),
    "swift": Lang("swift", "XCTest cases in the package's test target", (".swift",), "swift test",
                  "Tests/HeartgoldTests/Heartgold{Kind}Tests.swift", "swift test --filter '{name}'",
                  skip_ours="{test_cmd} --skip 'Heartgold'", markers=("Package.swift",)),
    "dotnet": Lang("dotnet", "xUnit tests in the solution's test project", (".cs",), "dotnet test",
                   "tests/Heartgold{Kind}Tests.cs", "dotnet test --filter 'FullyQualifiedName~{name}'",
                   skip_ours="{test_cmd} --filter 'FullyQualifiedName!~Heartgold'", markers=("*.sln", "*.slnx", "*.csproj")),
    "cpp": Lang("cpp", "CTest tests registered in CMakeLists.txt (add_test)", (".c", ".cc", ".cpp", ".h", ".hpp"),
                "cmake -S . -B build -DCMAKE_BUILD_TYPE=Release >/dev/null && cmake --build build -j >/dev/null && ctest --test-dir build --output-on-failure",
                "tests/heartgold_{kind}.cpp", "{test_cmd} -R '^{name}'", skip_ours="{test_cmd} -E '^heartgold_'",
                probe_path="tests/heartgold_probe.cpp",
                probe_cmd="cmake -S . -B build -DCMAKE_BUILD_TYPE=Release >/dev/null && cmake --build build --target heartgold_probe -j >/dev/null && ./build/heartgold_probe",
                markers=("CMakeLists.txt",)),
    "php": Lang("php", "PHPUnit tests", (".php",), "vendor/bin/phpunit", "tests/Heartgold{Kind}Test.php", "path",
                probe_path=".heartgold_probe.php", probe_cmd="php .heartgold_probe.php", markers=("composer.json", "phpunit.xml")),
}


def detect(repo: pathlib.Path) -> Lang:
    """The repo's main language: root markers first, then the most common source extension."""
    repo = pathlib.Path(repo)
    present = [l for l in LANGS.values() if any(list(repo.glob(m)) for m in l.markers)]
    skip = {".git", "node_modules", ".venv", "venv", "target", "build", "dist", "vendor", ".heartgold"}
    counts: dict[str, int] = {}
    for p in repo.rglob("*"):
        if p.is_file() and not (set(p.relative_to(repo).parts) & skip):
            for l in LANGS.values():
                if p.suffix in l.exts:
                    counts[l.name] = counts.get(l.name, 0) + 1
    pool = present or [LANGS[n] for n in counts]
    if not pool:
        return LANGS["python"]
    lang = max(pool, key=lambda l: counts.get(l.name, 0))
    cmd = lang.test_cmd or (_py_cmd() if lang.name == "python" else _js_cmd(repo))
    if lang.name == "php" and not (repo / "vendor" / "bin" / "phpunit").exists():
        cmd = "phpunit"
    return Lang(**{**lang.__dict__, "test_cmd": cmd})


_COUNTS = [
    # (passed, failed) patterns, in the order runners print them
    (r"test result: \w+\. (\d+) passed; (\d+) failed", "cargo"),
    (r"Tests run: (\d+), Failures: (\d+), Errors: (\d+)", "maven"),
    (r"(\d+) examples?, (\d+) failures?", "rspec"),
    (r"Executed (\d+) tests?, with (\d+) failures?", "xctest"),
    (r"Failed:\s+(\d+),\s+Passed:\s+(\d+)", "dotnet"),
    (r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", "ctest"),
    (r"[#ℹ] pass (\d+)", "node"),
]


def parse_results(out: str) -> tuple[int, int, list]:
    """Passed, failed and failing test names, from any supported runner's output."""
    passed = failed = 0
    if m := re.findall(_COUNTS[0][0], out):
        passed, failed = sum(int(a) for a, _ in m), sum(int(b) for _, b in m)
    elif m := re.findall(_COUNTS[1][0], out):
        run, fl, er = map(int, m[-1])  # the last line is Maven's total
        passed, failed = run - fl - er, fl + er
    elif m := re.findall(_COUNTS[2][0], out):
        ex, fl = map(int, m[-1])
        passed, failed = ex - fl, fl
    elif m := re.findall(_COUNTS[3][0], out):
        ex, fl = map(int, m[-1])
        passed, failed = ex - fl, fl
    elif m := re.findall(_COUNTS[4][0], out):
        failed, passed = map(int, m[-1])
    elif m := re.findall(_COUNTS[5][0], out):
        pct, fl, total = map(int, m[-1])
        passed, failed = total - fl, fl
    elif m := re.findall(r"100% tests passed out of (\d+)", out):  # ctest, all green
        passed = int(m[-1])
    elif "--- PASS:" in out or "--- FAIL:" in out:
        passed, failed = out.count("--- PASS:"), out.count("--- FAIL:")
    elif re.search(_COUNTS[6][0], out):
        passed = sum(int(x) for x in re.findall(r"[#ℹ] pass (\d+)", out))
        failed = sum(int(x) for x in re.findall(r"[#ℹ] fail (\d+)", out))
    elif m := re.findall(r"OK \((\d+) tests?", out):  # phpunit, all green
        passed = int(m[-1])
    elif m := re.findall(r"Tests: (\d+), Assertions: \d+, (?:Errors: (\d+), )?Failures: (\d+)", out):
        t, e, f = m[-1]
        failed = int(f) + int(e or 0)
        passed = int(t) - failed
    else:
        # pytest, vitest, jest: "N passed", "N failed" anywhere in the summary
        passed = sum(int(n) for n in re.findall(r"(\d+) passed", out))
        failed = sum(int(n) for n in re.findall(r"(\d+) (?:failed|errors?)\b", out))
    names = (re.findall(r"^(?:FAILED|ERROR) (\S+)", out, re.M)                 # pytest
             + re.findall(r"^test (\S+) \.\.\. FAILED", out, re.M)            # cargo
             + re.findall(r"--- FAIL: (\S+)", out)                            # go
             + re.findall(r"^\s*(?:×|✕|✗) (.+?)(?:\s+\d+ms)?$", out, re.M)  # vitest, jest
             + re.findall(r"^rspec \./(\S+)", out, re.M))                     # rspec
    return passed, failed, names
