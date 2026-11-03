"""Benchmark runner: run one tool on every fixture under the same budget and score it.

Usage: python bench/run.py --tool repoforge [--fixtures semver lru] [--budget-usd 3] [--jobs 3]
"""
import argparse, concurrent.futures as cf, datetime, json, math, os, pathlib, re, shutil, subprocess, sys, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = ROOT / "bench" / "fixtures"
PY = str(ROOT / ".venv" / "bin" / "python")
COMPETITORS = pathlib.Path(os.environ.get("REPOFORGE_COMPETITORS", ROOT / "bench" / "competitors"))
BENCH_TIMEOUT = 60
MODEL = os.environ.get("BENCH_MODEL", "sonnet")
# Same isolation for every tool: no user plugins/hooks/MCP, only the project's own settings.
CLAUDE = ["claude", "-p", "--model", MODEL, "--dangerously-skip-permissions",
          "--setting-sources", "project", "--strict-mcp-config", "--no-session-persistence",
          "--output-format", "stream-json", "--verbose"]
TEST_CMD = f"{PY} -m pytest -q -p no:cacheprovider --timeout=30 tests"


def sh(cmd, cwd, timeout, env=None):
    t = time.time()
    try:
        p = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True,
                           timeout=timeout, env={**os.environ, **(env or {})})
        return p.returncode, p.stdout + p.stderr, time.time() - t
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        return -9, out, time.time() - t


def pytest_counts(cwd, path):
    code, out, _ = sh(f"{PY} -m pytest -q -p no:cacheprovider --timeout=30 {path}", cwd, 600)
    passed = sum(int(n) for n in re.findall(r"(\d+) passed", out))
    failed = sum(int(n) for n in re.findall(r"(\d+) (?:failed|error)", out))
    total = passed + failed
    return passed, total


def bench_time(cwd):
    if not (pathlib.Path(cwd) / "bench.py").exists():
        return None
    times = []
    for _ in range(3):
        code, out, wall = sh(f"{PY} bench.py", cwd, BENCH_TIMEOUT)
        if code != 0:
            return float(BENCH_TIMEOUT)
        try:
            times.append(float(out.strip().splitlines()[-1]))
        except ValueError:
            return float(BENCH_TIMEOUT)
    return min(times)


# ---- adapters: each runs the tool inside `work` and returns (cost_usd, transcript)

def claude_run(prompt, work, budget, timeout):
    code, out, _ = sh(CLAUDE + ["--max-budget-usd", str(budget), prompt], work, timeout)
    cost = 0.0
    for line in out.splitlines():
        if '"type":"result"' in line.replace(" ", ""):
            try:
                cost = json.loads(line).get("total_cost_usd", 0.0) or 0.0
            except json.JSONDecodeError:
                pass
    return cost, out


def adapter_noop(work, goal, budget, timeout):
    return 0.0, ""


def adapter_plain_claude(work, goal, budget, timeout):
    prompt = (f"{goal}\n\nWork only inside the current directory. Run the tests with:\n{TEST_CMD}\n"
              "When you are done, all tests must pass. Add tests for what you changed.")
    return claude_run(prompt, work, budget, timeout)


def adapter_autoresearch(work, goal, budget, timeout):
    skill = COMPETITORS / "autoresearch" / ".claude" / "skills" / "autoresearch"
    dst = pathlib.Path(work) / ".claude" / "skills" / "autoresearch"
    shutil.copytree(skill, dst)
    sh("git add -A && git commit -qm 'add skill'", work, 30)
    prompt = (f"/autoresearch\nGoal: {goal.strip()}\n"
              f"Metric: number of passing tests (higher is better)\n"
              f"Verify: {TEST_CMD} 2>&1 | tail -1\nIterations: 15")
    return claude_run(prompt, work, budget, timeout)


def adapter_repoforge(work, goal, budget, timeout):
    code, out, _ = sh([PY, "-m", "repoforge", "run", ".", "--goal-file", "goal.md",
                       "--budget-usd", str(budget), "--model", MODEL], work, timeout,
                      env={"PYTHONPATH": str(ROOT)})
    cost = 0.0
    m = re.findall(r"REPOFORGE_COST_USD=([\d.]+)", out)
    if m:
        cost = float(m[-1])
    return cost, out


ADAPTERS = {"noop": adapter_noop, "plain-claude": adapter_plain_claude,
            "autoresearch": adapter_autoresearch, "repoforge": adapter_repoforge}


def run_fixture(tool, name, budget, timeout):
    fx = FIX / name
    work = pathlib.Path(tempfile.mkdtemp(prefix=f"rf-{name}-"))
    shutil.copytree(fx / "repo", work, dirs_exist_ok=True)
    sh("git init -q && git add -A && git -c user.email=b@b -c user.name=bench commit -qm base", work, 30)
    goal = (fx / "repo" / "goal.md").read_text()
    base_time = bench_time(work)
    t0 = time.time()
    cost, transcript = ADAPTERS[tool](str(work), goal, budget, timeout)
    elapsed = time.time() - t0
    contaminated = bool(re.search(r"repoforge/bench/(fixtures/[^/]+/hidden|reference)", transcript))
    # restore the original visible tests (a tool may not "pass" by editing them), then add hidden tests
    for f in (fx / "repo" / "tests").iterdir():
        shutil.copy(f, work / "tests" / f.name)
    vis_p, vis_t = pytest_counts(work, " ".join(f"tests/{f.name}" for f in (fx / "repo" / "tests").iterdir()))
    hid_dir = work / "_hidden_tests"
    shutil.copytree(fx / "hidden", hid_dir)
    shutil.copy(next(hid_dir.glob("test_*.py")), work / "tests" / "_hidden_check.py")
    hid_p, hid_t = pytest_counts(work, "tests/_hidden_check.py")
    after_time = bench_time(work)
    meta = json.loads((fx / "meta.json").read_text()) if (fx / "meta.json").exists() else {}
    speed = None
    if base_time and after_time:
        speedup = base_time / max(after_time, 1e-6)
        ref = meta.get("ref_speedup", 10.0)
        speed = max(0.0, min(1.0, math.log(max(speedup, 1e-9)) / math.log(ref)))
    hidden = hid_p / hid_t if hid_t else 0.0
    if "noop_pass" in meta and hid_t > meta["noop_pass"]:
        # hard suite: fraction of the gap between the naive code and perfect that the tool closed
        hidden = max(0.0, (hid_p - meta["noop_pass"]) / (hid_t - meta["noop_pass"]))
    clean = 1.0 if vis_t and vis_p == vis_t else 0.0
    score = (0.7 * hidden + 0.2 * speed + 0.1 * clean) if speed is not None else (0.9 * hidden + 0.1 * clean)
    res = dict(fixture=name, hidden=round(hidden, 3), hidden_raw=f"{hid_p}/{hid_t}",
               visible=f"{vis_p}/{vis_t}", speed=None if speed is None else round(speed, 3),
               base_time=base_time, after_time=after_time, cost_usd=round(cost, 3),
               seconds=round(elapsed), contaminated=contaminated, score=round(score, 3), work=str(work))
    (work / "_bench_transcript.txt").write_text(transcript)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", required=True, choices=ADAPTERS)
    ap.add_argument("--fixtures", nargs="*")
    ap.add_argument("--budget-usd", type=float, default=3.0)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--suite", default="hard", help="easy | hard | all")
    a = ap.parse_args()
    def suite(p):
        m = p / "meta.json"
        return json.loads(m.read_text()).get("suite", "easy") if m.exists() else "easy"
    names = a.fixtures or sorted(p.name for p in FIX.iterdir() if p.is_dir() and a.suite in ("all", suite(p)))
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        results = list(ex.map(lambda n: run_fixture(a.tool, n, a.budget_usd, a.timeout), names))
    total = sum(r["score"] for r in results) / len(results)
    out = dict(tool=a.tool, suite=a.suite, model=MODEL, budget_usd=a.budget_usd, when=datetime.datetime.now().isoformat(timespec="seconds"),
               score=round(total, 3), results=results)
    rd = ROOT / "bench" / "results"
    rd.mkdir(exist_ok=True)
    path = rd / f"{a.suite}-{a.tool}-{datetime.datetime.now():%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps(out, indent=2))
    for r in results:
        print(f"{r['fixture']:10} score={r['score']:.3f} hidden={r['hidden_raw']:>6} visible={r['visible']:>4} "
              f"speed={r['speed']} cost=${r['cost_usd']} {r['seconds']}s{' CONTAMINATED' if r['contaminated'] else ''}")
    print(f"TOTAL {a.tool}: {total:.3f}  -> {path}")


if __name__ == "__main__":
    main()
