"""The heartgold pipeline (v2).

map -> research (passages + cited requirements + FULL spec text) -> spec tests -> 3 diverse candidates
-> differential testing (probe all candidates, a spec-reading judge settles every disagreement, verdicts
become exact-value tests) -> pick best -> fix -> second diff round -> optimize -> gate -> merge.
"""
import datetime, importlib.util, json, pathlib, re, shlex, shutil, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor

from .agent import COST, claude, extract_json
from .diff import disagreements, tests_from_verdicts
from .research import fetch_specs, research

SPEC_TEST = "tests/test_heartgold_spec.py"
DIFF_TEST = "tests/test_heartgold_diff.py"
ADV_TEST = "tests/test_heartgold_adversarial.py"
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".heartgold", ".claude"}
STYLES = [
    "Make the smallest correct change to the existing code.",
    "Do a clean, well-structured rewrite of the affected code if that is more robust.",
    "Work spec-first: read the specification text end to end, write down its grammar and every rule "
    "(including what must be REJECTED), then implement each rule literally, in the spec's order.",
]


def sh(cmd, cwd, timeout=600):
    try:
        p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired as e:
        return -9, str(e.stdout or "")


class Run:
    def __init__(self, repo, goal, model="sonnet", budget=3.0, candidates=3, diff_rounds=2,
                 test_cmd=None, bench_cmd=None):
        self.repo = pathlib.Path(repo).resolve()
        self.goal, self.model, self.budget = goal, model, budget
        self.n_cand, self.diff_rounds = candidates, diff_rounds
        self.state = self.repo / ".heartgold"
        self.state.mkdir(exist_ok=True)
        (self.state / ".gitignore").write_text("*\n")
        self.spec_dir = self.state / "spec"
        self.ledger = self.state / "ledger.jsonl"
        self.test_cmd, self.bench_cmd = test_cmd, bench_cmd
        self.t0 = time.time()

    # ---------- bookkeeping
    def log(self, event, **kw):
        rec = dict(t=round(time.time() - self.t0, 1), event=event, usd=round(COST["usd"], 3), **kw)
        with self.ledger.open("a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        print(f"[heartgold {rec['t']:>6}s ${rec['usd']:.2f}] {event} " +
              " ".join(f"{k}={v}" for k, v in kw.items() if k != "detail")[:300], flush=True)

    def left(self):
        return self.budget - COST["usd"]

    def slice(self, frac):
        return max(0.05, min(self.left(), self.budget * frac))

    def spec_note(self):
        if self.spec_dir.exists() and any(self.spec_dir.iterdir()):
            return (f"\nThe FULL text of the authoritative specification(s) is in {self.spec_dir}/ - read it; "
                    "it overrides your memory wherever they differ.\n")
        return ""

    # ---------- map
    def detect(self):
        if self.test_cmd is None:
            if any(self.repo.glob("**/*.py")):
                extra = " --timeout=60" if importlib.util.find_spec("pytest_timeout") else ""
                self.test_cmd = f"{sys.executable} -m pytest -q -p no:cacheprovider{extra}"
            elif (self.repo / "package.json").exists():
                self.test_cmd = "npm test --silent"
            elif (self.repo / "Cargo.toml").exists():
                self.test_cmd = "cargo test -q"
            elif (self.repo / "go.mod").exists():
                self.test_cmd = "go test ./..."
        if self.bench_cmd is None and (self.repo / "bench.py").exists():
            self.bench_cmd = f"{sys.executable} bench.py"
        files = [p for p in sorted(self.repo.rglob("*")) if p.is_file()
                 and not (set(p.relative_to(self.repo).parts) & SKIP_DIRS)
                 and p.suffix in {".py", ".js", ".ts", ".go", ".rs", ".md", ".toml", ".json", ".java", ".rb"}]
        rel = [str(p.relative_to(self.repo)) for p in files]
        self.orig_tests = [r for r in rel if re.search(r"(^|/)tests?/|(^|/)test_|_test\.", r)]
        self.py_modules = [r for r in rel if r.endswith(".py") and r not in self.orig_tests and r != "bench.py"]
        chunks, total = [], 0
        for p in files:
            txt = p.read_text(errors="replace")
            if total + len(txt) > 60000:
                break
            chunks.append(f"--- {p.relative_to(self.repo)}\n{txt}")
            total += len(txt)
        self.code = "\n".join(chunks)
        gitdir = pathlib.Path(sh("git rev-parse --git-common-dir", self.repo)[1].strip())
        gitdir = gitdir if gitdir.is_absolute() else self.repo / gitdir
        (gitdir / "info").mkdir(exist_ok=True)
        excl = gitdir / "info" / "exclude"
        cur = excl.read_text() if excl.exists() else ""
        excl.write_text(cur + "".join(f"{x}\n" for x in ("__pycache__/", "*.pyc", ".heartgold/", ".pytest_cache/") if x not in cur))
        sh("git add -A && git -c user.email=rf@rf -c user.name=heartgold commit -qm 'heartgold: baseline' --allow-empty", self.repo)
        self.base = sh("git rev-parse HEAD", self.repo)[1].strip()
        self.log("map", test_cmd=self.test_cmd, bench_cmd=self.bench_cmd, files=len(files), orig_tests=self.orig_tests)

    # ---------- measuring
    def tests(self, cwd, path=""):
        code, out = sh(f"{self.test_cmd} {path}".strip(), cwd, 900)
        passed = sum(int(n) for n in re.findall(r"(\d+) passed", out))
        failed = sum(int(n) for n in re.findall(r"(\d+) (?:failed|errors?)\b", out))
        names = re.findall(r"^(?:FAILED|ERROR) (\S+)", out, re.M)
        return dict(passed=passed, failed=failed, ok=(code == 0 and failed == 0), failing=names, tail=out[-3000:])

    def bench(self, cwd):
        if not self.bench_cmd:
            return None
        best = None
        for _ in range(3):
            code, out = sh(self.bench_cmd, cwd, 120)
            try:
                v = float(out.strip().splitlines()[-1]) if code == 0 else float("inf")
            except (ValueError, IndexError):
                v = float("inf")
            best = v if best is None else min(best, v)
        return best

    def gate(self, wt):
        """Score a worktree. Original tests are restored first, so editing them cannot buy a pass."""
        wt = pathlib.Path(wt)
        if self.orig_tests:
            sh(f"git checkout {self.base} -- " + " ".join(map(shlex.quote, self.orig_tests)), wt)
        empty = dict(ok=True, passed=0, failed=0, failing=[], tail="")
        orig = self.tests(wt, " ".join(map(shlex.quote, self.orig_tests))) if self.orig_tests else empty
        res = {"orig": orig}
        for k, f in (("spec", SPEC_TEST), ("diff", DIFF_TEST), ("adv", ADV_TEST)):
            res[k] = self.tests(wt, f) if (wt / f).exists() else dict(empty)
        t = self.bench(wt)
        # differential tests were judged against the spec text, so they count double
        passed = res["spec"]["passed"] + 2 * res["diff"]["passed"] + res["adv"]["passed"]
        failed = res["spec"]["failed"] + 2 * res["diff"]["failed"] + res["adv"]["failed"]
        res["key"] = (1 if orig["ok"] else 0, passed - failed, passed, -(t if t is not None else 0))
        res["bench"] = t
        return res

    def failing(self, g):
        return [x for k in ("orig", "spec", "diff", "adv") for x in g[k].get("failing", [])]

    # ---------- worktrees
    def worktree(self, name, ref=None):
        path = pathlib.Path(tempfile.mkdtemp(prefix=f"rf-{name}-"))
        shutil.rmtree(path)
        sh(f"git worktree add -q --detach {shlex.quote(str(path))} {ref or self.base}", self.repo)
        return path

    def drop_worktree(self, wt):
        sh(f"git worktree remove --force {shlex.quote(str(wt))}", self.repo)

    def commit(self, wt, msg):
        sh(f"git add -A && git -c user.email=rf@rf -c user.name=heartgold commit -qm {shlex.quote(msg)}", wt)
        return self.head(wt)

    def head(self, wt):
        return sh("git rev-parse HEAD", wt)[1].strip()

    # ---------- phases
    def write_spec_tests(self, reqs):
        wt = self.worktree("spec")
        claude(
            f"Goal:\n{self.goal}\n{self.spec_note()}\nRequirements from web research ('verified' ones are backed "
            f"by a quoted source):\n{json.dumps(reqs, indent=1)}\n\n"
            f"Write {SPEC_TEST}: one focused test per requirement (name tests after the requirement id), "
            "testing ONLY the public API named in the goal / existing code, with exact expected values taken from "
            "the specification. These tests define 'done' for an implementer who will not see your reasoning: be "
            "precise and faithful to the spec; never contradict the goal or the existing tests; leave out anything "
            f"you are unsure about. Do NOT change any other file. Make sure the file imports and collects: "
            f"{self.test_cmd} {SPEC_TEST} (failures against the current code are expected).",
            wt, self.model, self.slice(0.07))
        ok = (wt / SPEC_TEST).exists()
        if ok:
            shutil.copy(wt / SPEC_TEST, self.state / "spec_tests.py")
        self.drop_worktree(wt)
        self.log("spec_tests", written=ok)
        return ok

    def implement(self, i, reqs, perf_hint):
        wt = self.worktree(f"cand{i}")
        if (self.state / "spec_tests.py").exists():
            shutil.copy(self.state / "spec_tests.py", wt / SPEC_TEST)
        claude(
            f"Goal:\n{self.goal}\n{self.spec_note()}\nRequirements from web research:\n{json.dumps(reqs, indent=1)}\n\n"
            f"Implement the goal in this repository. {STYLES[i % len(STYLES)]} {perf_hint}\n"
            f"Done means ALL of these pass: {self.test_cmd}\n"
            f"({SPEC_TEST} encodes the researched requirements. If you are CERTAIN a test there contradicts the "
            "specification, leave it failing; never edit it to make it pass. Never edit or delete the pre-existing "
            "tests.) Keep public function/class signatures compatible.",
            wt, self.model, self.slice(0.15), timeout=1500)
        self.commit(wt, f"heartgold candidate {i}")
        g = self.gate(wt)
        self.log("candidate", i=i, key=g["key"], orig_ok=g["orig"]["ok"], failing=self.failing(g)[:12], bench=g["bench"])
        return [wt, g]

    def make_probe(self, wt):
        probe = self.state / "probe.json"
        if probe.exists():
            return probe
        mods = ", ".join(self.py_modules) or "(none)"
        claude(
            f"Goal:\n{self.goal}\n{self.spec_note()}\nModules: {mods}\n\n"
            f"Write {probe} as JSON: {{\"setup\": \"<python import lines for the public API>\", \"exprs\": [...]}}. "
            "`exprs` is a list of 200-400 short Python expressions that call the public API and return a plain "
            "value (str/int/bool/list/tuple), e.g. str(...), comparisons, list(...). Cover every rule and corner of "
            "the specification: each grammar branch, boundaries, invalid input that must be rejected, alternative "
            "spellings, ordering, combinations of features, unicode, empty input. Generate them with a small script "
            "if that helps (delete the script after). Expressions must be deterministic and run fast. Only write "
            f"{probe}; do not modify the repository.",
            str(wt), self.model, self.slice(0.06), timeout=900)
        try:
            data = json.loads(probe.read_text())
            assert isinstance(data.get("exprs"), list) and data.get("setup")
        except Exception:
            probe.unlink(missing_ok=True)
            return None
        self.log("probe", exprs=len(data["exprs"]))
        return probe

    def diff_round(self, cands, rnd):
        """Find inputs where candidates disagree; a judge decides; verdicts become tests for everyone."""
        probe = self.make_probe(cands[0][0])
        if not probe:
            return 0
        rows, n_dis, n_all = disagreements([c[0] for c in cands], probe)
        self.log("diff", round=rnd, disagree=n_dis, of=n_all)
        if not rows:
            return 0
        setup = json.loads(probe.read_text())["setup"]
        verdicts = []
        for k in range(0, len(rows), 20):
            batch = rows[k:k + 20]
            listing = "\n".join(f"{j}. {r['expr']}\n   candidate outputs: " +
                                "; ".join(f"#{c}: {o}" for c, o in sorted(r["outputs"].items()))
                                for j, r in enumerate(batch))
            reply = claude(
                f"Goal:\n{self.goal}\n{self.spec_note()}\nSetup: {setup}\n\nSeveral implementations disagree on these "
                "expressions ('=' prefix: returned repr; '!' prefix: raised that exception type):\n" + listing +
                "\n\nFor each, decide the CORRECT result strictly from the specification text (quote the rule you "
                "used in `why`). The right answer may differ from every candidate. Use 'unsure' if the spec does not "
                "settle it. Do not modify files. Reply only with JSON: "
                '{"verdicts": [{"i": 0, "expected": "=<python repr>" | "!<ExceptionName>" | "unsure", "why": "..."}]}',
                str(self.repo), self.model, self.slice(0.04), tools=["Read", "Grep", "Glob"])
            for v in (extract_json(reply, {}) or {}).get("verdicts", []):
                if isinstance(v.get("i"), int) and 0 <= v["i"] < len(batch):
                    v["expr"] = batch[v["i"]]["expr"]
                    verdicts.append(v)
        src, n = tests_from_verdicts(setup, verdicts)
        prev_p = self.state / "diff_tests.py"
        if prev_p.exists():
            body = src.split("\n\n\n", 1)[-1].replace("def test_diff_", f"def test_diff_r{rnd}_")
            src = prev_p.read_text() + "\n" + body
        prev_p.write_text(src)
        for c in cands:
            shutil.copy(prev_p, c[0] / DIFF_TEST)
            self.commit(c[0], f"heartgold: differential tests round {rnd}")
            c[1] = self.gate(c[0])
        self.log("diff_tests", round=rnd, new=n, keys=[c[1]["key"] for c in cands])
        return n

    def fix(self, wt, g, what):
        before = self.head(wt)
        fails = self.failing(g)
        if not fails:
            return g
        tails = "\n".join(g[k].get("tail", "")[-1500:] for k in ("orig", "spec", "diff", "adv") if g[k].get("failing"))
        claude(
            f"Goal:\n{self.goal}\n{self.spec_note()}\n{what}\nThese tests fail:\n" + "\n".join(fails[:60]) +
            f"\n\nTest output tail:\n{tails[-4000:]}\n"
            f"Fix the CODE so they pass (do not edit tests). {DIFF_TEST} was decided against the specification and "
            f"is the most trustworthy. Run: {self.test_cmd}",
            wt, self.model, self.slice(0.1), timeout=1500)
        self.commit(wt, "heartgold fix")
        g2 = self.gate(wt)
        if g2["key"] < g["key"]:
            sh(f"git reset -q --hard {before}", wt)
            self.log("fix", kept=False, before=g["key"], after=g2["key"])
            return g
        self.log("fix", kept=True, before=g["key"], after=g2["key"])
        return g2

    def optimize(self, wt, g):
        if not self.bench_cmd or not g["orig"]["ok"] or g["bench"] in (None, float("inf")):
            return g
        before = self.head(wt)
        claude(
            f"Goal:\n{self.goal}\n\nMake the code faster on `{self.bench_cmd}` (prints seconds, currently {g['bench']:.4f}). "
            "Think about algorithmic complexity first (right data structure, avoiding repeated work, early exits, "
            "pruning), then constant factors. All tests must still pass: " + self.test_cmd + ". Do not edit tests.",
            wt, self.model, self.slice(0.08), timeout=1200)
        self.commit(wt, "heartgold optimize")
        g2 = self.gate(wt)
        better = g2["key"][:2] >= g["key"][:2] and g2["orig"]["ok"] and g2["bench"] < g["bench"] * 0.97
        self.log("optimize", before=g["bench"], after=g2["bench"], kept=better)
        if not better:
            sh(f"git reset -q --hard {before}", wt)
            return g
        return g2

    # ---------- main
    def run(self):
        self.detect()
        base = self.gate(self.repo)
        self.log("baseline", key=base["key"], bench=base["bench"])
        reqs, passages = research(self.goal, self.code, str(self.repo), self.model, self.budget, self.log)
        (self.state / "requirements.json").write_text(json.dumps(reqs, indent=1))
        fetch_specs(self.goal, passages, str(self.repo), self.model, self.slice(0.02), self.log, self.spec_dir)
        self.write_spec_tests(reqs)
        perf_hint = ("Also make it fast: `" + self.bench_cmd + "` prints seconds (lower is better).") if self.bench_cmd else ""
        with ThreadPoolExecutor(self.n_cand) as ex:
            cands = list(ex.map(lambda i: self.implement(i, reqs, perf_hint), range(self.n_cand)))
        for rnd in range(1, self.diff_rounds + 1):
            if len(cands) < 2 or self.left() < self.budget * 0.15:
                break
            self.diff_round(cands, rnd)
            cands.sort(key=lambda c: c[1]["key"], reverse=True)
            cands[0][1] = self.fix(cands[0][0], cands[0][1], "Some required tests still fail.")
            if rnd < self.diff_rounds and len(cands) > 2:
                self.drop_worktree(cands.pop()[0])  # keep the stronger candidates for the next round
        cands.sort(key=lambda c: c[1]["key"], reverse=True)
        wt, g = cands[0]
        self.log("winner", key=g["key"], others=[c[1]["key"] for c in cands[1:]])
        for c in cands[1:]:
            self.drop_worktree(c[0])
        if self.left() > self.budget * 0.1 and self.failing(g):
            g = self.fix(wt, g, "Some required tests still fail.")
        if self.left() > self.budget * 0.06:
            g = self.optimize(wt, g)
        final = self.head(wt)
        keep = g["orig"]["ok"] and g["key"][1] >= base["key"][1]
        if keep:
            code, out = sh(f"git merge -q --ff-only {final}", self.repo)
            if code != 0:
                code, out = sh(f"git checkout -q {final} -- . && git -c user.email=rf@rf -c user.name=heartgold "
                               "commit -qam 'heartgold: apply winner'", self.repo)
            if code != 0:
                keep = False
                self.log("merge_failed", detail=out[-500:])
        self.drop_worktree(wt)
        self.log("done", kept=keep, key=g["key"], bench=g["bench"])
        self.report(reqs, base, g, keep)
        print(f"HEARTGOLD_COST_USD={COST['usd']:.4f}")
        return keep

    def report(self, reqs, base, g, keep):
        lines = [f"# heartgold report - {datetime.datetime.now():%Y-%m-%d %H:%M}", "", f"Goal: {self.goal.strip()}", "",
                 f"Result: {'merged' if keep else 'NOT merged'} - cost ${COST['usd']:.2f}", "",
                 f"- original tests: {'pass' if g['orig']['ok'] else 'FAIL'}",
                 f"- spec tests passed: {g['spec']['passed']} - differential tests passed: {g['diff']['passed']}",
                 f"- bench: {base['bench']} -> {g['bench']}", "", "## Specification sources", ""]
        if self.spec_dir.exists():
            for f in sorted(self.spec_dir.iterdir()):
                lines.append("- " + f.read_text().split("\n", 1)[0].replace("Source: ", ""))
        lines += ["", "## Requirements", ""]
        for r in reqs:
            src = f" - [{r['url']}]({r['url']}): \"{r['quote']}\"" if r.get("verified") else " - (unsourced)"
            lines.append(f"- **{r.get('id')}** {r.get('text')}{src}")
        (self.state / "report.md").write_text("\n".join(lines) + "\n")
