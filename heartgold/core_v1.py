"""The heartgold pipeline: map -> research -> spec tests -> candidates -> judge -> adversarial -> perf -> merge."""
import datetime, importlib.util, json, pathlib, re, shlex, shutil, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor

from .agent import COST, claude, extract_json
from .research import research

SPEC_TEST = "tests/test_heartgold_spec.py"
ADV_TEST = "tests/test_heartgold_adversarial.py"
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".heartgold", ".claude"}


def sh(cmd, cwd, timeout=600):
    try:
        p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired as e:
        return -9, str(e.stdout or "")


class Run:
    def __init__(self, repo, goal, model="sonnet", budget=3.0, candidates=2, adv_rounds=2,
                 test_cmd=None, bench_cmd=None):
        self.repo = pathlib.Path(repo).resolve()
        self.goal, self.model, self.budget = goal, model, budget
        self.n_cand, self.adv_rounds = candidates, adv_rounds
        self.state = self.repo / ".heartgold"
        self.state.mkdir(exist_ok=True)
        (self.state / ".gitignore").write_text("*\n")
        self.ledger = self.state / "ledger.jsonl"
        self.test_cmd, self.bench_cmd = test_cmd, bench_cmd
        self.t0 = time.time()

    # ---------- bookkeeping
    def log(self, event, **kw):
        rec = dict(t=round(time.time() - self.t0, 1), event=event, cost=round(COST["usd"], 3), **kw)
        with self.ledger.open("a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        print(f"[heartgold {rec['t']:>6}s ${rec['cost']:.2f}] {event} " +
              " ".join(f"{k}={v}" for k, v in kw.items() if k not in ("detail",))[:300], flush=True)

    def left(self):
        return self.budget - COST["usd"]

    def slice(self, frac):
        return max(0.05, min(self.left(), self.budget * frac))

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
        self.orig_tests = [str(p.relative_to(self.repo)) for p in files if re.search(r"(^|/)tests?/|test_|_test\.", str(p.relative_to(self.repo)))]
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
        if self.orig_tests:
            sh(f"git checkout {self.base} -- " + " ".join(map(shlex.quote, self.orig_tests)), wt)
        orig = self.tests(wt, " ".join(map(shlex.quote, self.orig_tests))) if self.orig_tests else dict(ok=True, passed=0, failed=0)
        spec = self.tests(wt, SPEC_TEST) if (wt / SPEC_TEST).exists() else dict(ok=True, passed=0, failed=0, failing=[])
        adv = self.tests(wt, ADV_TEST) if (wt / ADV_TEST).exists() else dict(ok=True, passed=0, failed=0, failing=[])
        t = self.bench(wt)
        key = (1 if orig["ok"] else 0, spec["passed"] + adv["passed"], -(spec["failed"] + adv["failed"]),
               -(t if t is not None else 0))
        return dict(key=key, orig=orig, spec=spec, adv=adv, bench=t)

    # ---------- worktrees
    def worktree(self, name, ref=None):
        path = pathlib.Path(tempfile.mkdtemp(prefix=f"rf-{name}-"))
        shutil.rmtree(path)
        sh(f"git worktree add -q --detach {shlex.quote(str(path))} {ref or self.base}", self.repo)
        return path

    def commit(self, wt, msg):
        sh(f"git add -A && git -c user.email=rf@rf -c user.name=heartgold commit -qm {json.dumps(msg)}", wt)
        return sh("git rev-parse HEAD", wt)[1].strip()

    # ---------- phases
    def write_spec_tests(self, reqs):
        wt = self.worktree("spec")
        req_txt = json.dumps(reqs, indent=1)
        claude(
            f"Goal:\n{self.goal}\n\nRequirements (from web research; 'verified' ones are backed by a quoted source):\n{req_txt}\n\n"
            f"Write {SPEC_TEST}: one focused test per requirement (name tests after the requirement id), "
            "testing ONLY the public API named in the goal / existing code, with exact expected values. "
            "These tests define 'done' for an implementer who will not see your reasoning, so be precise and "
            "faithful to the source quotes and the goal text; never contradict the goal or the existing tests. "
            f"Do NOT change any other file. Check the file at least imports and collects with: {self.test_cmd} {SPEC_TEST} "
            "(failures against the current code are expected and fine).",
            wt, self.model, self.slice(0.08))
        ok = (wt / SPEC_TEST).exists()
        if ok:
            shutil.copy(wt / SPEC_TEST, self.state / "spec_tests.py")
        sh(f"git worktree remove --force {shlex.quote(str(wt))}", self.repo)
        self.log("spec_tests", written=ok)
        return ok

    def implement(self, i, reqs, perf_hint):
        wt = self.worktree(f"cand{i}")
        if (self.state / "spec_tests.py").exists():
            shutil.copy(self.state / "spec_tests.py", wt / SPEC_TEST)
        style = ["Make the smallest correct change.",
                 "Prefer a clean, well-structured rewrite of the affected functions if that is more robust."][i % 2]
        claude(
            f"Goal:\n{self.goal}\n\nResearched requirements:\n{json.dumps(reqs, indent=1)}\n\n"
            f"Implement the goal in this repository. {style} {perf_hint}\n"
            f"Done means ALL of these pass: {self.test_cmd}\n"
            f"({SPEC_TEST} encodes the researched requirements. If you are CERTAIN a test there contradicts the goal "
            "text, leave it failing and explain why in one line in HEARTGOLD_NOTES.md; never edit it to make it pass. "
            "Never edit or delete the pre-existing tests.) Keep public function/class signatures compatible.",
            wt, self.model, self.slice(0.22), timeout=1500)
        self.commit(wt, f"heartgold candidate {i}")
        g = self.gate(wt)
        self.log("candidate", i=i, key=g["key"], orig_ok=g["orig"]["ok"], spec_fail=g["spec"]["failing"], bench=g["bench"])
        return wt, g

    def judge(self, wt, failing, test_file):
        """Decide for each failing test whether the test or the code is wrong. Returns tests to drop."""
        if not failing:
            return []
        reply = claude(
            f"Goal:\n{self.goal}\n\nThese tests in {test_file} fail against the implementation:\n" + "\n".join(failing) +
            f"\n\nRead {test_file} and the code. For each failing test decide: is the TEST wrong (it contradicts the "
            "goal text, the existing tests, or the authoritative spec) or is the CODE wrong? Be strict: when the "
            "goal or a well-known spec supports the test, the code is wrong. Do not modify files. "
            'Reply only with JSON: {"verdicts": [{"test": "<test function name>", "wrong": "test"|"code", "why": "..."}]}',
            wt, self.model, self.slice(0.04), tools=["Read", "Grep", "Glob"])
        verdicts = (extract_json(reply, {}) or {}).get("verdicts", [])
        drop = [v["test"].split("::")[-1] for v in verdicts if v.get("wrong") == "test"]
        self.log("judge", file=test_file, failing=len(failing), drop=drop)
        return drop

    def drop_tests(self, wt, test_file, names):
        """Remove test functions by name (python) so a bad test cannot block a good change."""
        p = wt / test_file
        if not names or not p.exists():
            return
        src = p.read_text()
        for n in names:
            src = re.sub(rf"(?ms)^(def {re.escape(n)}\(.*?)(?=^def |^class |\Z)", "", src)
        p.write_text(src)

    def fix(self, wt, g, what):
        failing = (g["orig"].get("failing") or []) + g["spec"].get("failing", []) + g["adv"].get("failing", [])
        claude(
            f"Goal:\n{self.goal}\n\n{what}\nThese tests fail:\n" + "\n".join(failing) +
            f"\n\nTest output tail:\n{g['spec'].get('tail', '')[-1500:]}\n{g['adv'].get('tail', '')[-1500:]}\n"
            f"Fix the CODE so they pass (do not edit tests). Run: {self.test_cmd}",
            wt, self.model, self.slice(0.08), timeout=1200)
        self.commit(wt, "heartgold fix")
        return self.gate(wt)

    def adversarial(self, wt, reqs, rnd):
        existing = (wt / ADV_TEST).read_text() if (wt / ADV_TEST).exists() else ""
        claude(
            f"You are a hostile reviewer. Goal the code claims to meet:\n{self.goal}\n\n"
            f"Researched requirements:\n{json.dumps(reqs, indent=1)}\n\n"
            "Read the implementation and try to BREAK it: find inputs where it violates the goal or the authoritative "
            "spec (boundaries, empty/huge input, invalid input, ordering, unicode, timing/clock edges, state left "
            "behind, complexity blowups). " + (f"Append new tests to {ADV_TEST}" if existing else f"Write {ADV_TEST}") +
            " with up to 8 NEW tests, each with exact expected values justified by the goal or spec (cite in a comment). "
            f"Run them: {self.test_cmd} {ADV_TEST}. Keep only tests you are confident are correct. Do not modify any non-test file.",
            wt, self.model, self.slice(0.07))
        self.commit(wt, f"heartgold adversarial round {rnd}")
        g = self.gate(wt)
        self.log("adversarial", round=rnd, adv_fail=g["adv"]["failing"])
        return g

    def optimize(self, wt, g):
        if not self.bench_cmd or not g["orig"]["ok"]:
            return g
        before_sha = sh("git rev-parse HEAD", wt)[1].strip()
        claude(
            f"Goal:\n{self.goal}\n\nMake the code faster on `{self.bench_cmd}` (prints seconds, currently {g['bench']:.4f}). "
            "Think about algorithmic complexity first (right data structure, avoiding repeated work, early exits, "
            "pruning), then constant factors. All tests must still pass: " + self.test_cmd + ". Do not edit tests.",
            wt, self.model, self.slice(0.1), timeout=1200)
        self.commit(wt, "heartgold optimize")
        g2 = self.gate(wt)
        better = g2["key"][:3] >= g["key"][:3] and g2["orig"]["ok"] and g2["bench"] < g["bench"] * 0.97
        self.log("optimize", before=g["bench"], after=g2["bench"], kept=better)
        if not better:
            sh(f"git reset -q --hard {before_sha}", wt)
            return g
        return g2

    # ---------- main
    def run(self):
        self.detect()
        base = self.gate(self.repo)
        self.log("baseline", key=base["key"], bench=base["bench"])
        reqs, _ = research(self.goal, self.code, str(self.repo), self.model, self.budget, self.log)
        (self.state / "requirements.json").write_text(json.dumps(reqs, indent=1))
        self.write_spec_tests(reqs)
        perf_hint = "Also make it fast: `" + self.bench_cmd + "` prints seconds (lower is better)." if self.bench_cmd else ""
        with ThreadPoolExecutor(self.n_cand) as ex:
            cands = list(ex.map(lambda i: self.implement(i, reqs, perf_hint), range(self.n_cand)))
        # spec tests that fail on EVERY candidate are suspicious: judge them, drop the wrong ones everywhere
        common = set.intersection(*[set(g["spec"]["failing"]) for _, g in cands]) if cands else set()
        if common:
            drop = self.judge(cands[0][0], sorted(common), SPEC_TEST)
            cands = [(wt, (self.drop_tests(wt, SPEC_TEST, drop), self.commit(wt, "heartgold: drop wrong spec tests"), self.gate(wt))[2])
                     for wt, g in cands]
        cands.sort(key=lambda c: c[1]["key"], reverse=True)
        wt, g = cands[0]
        self.log("winner", key=g["key"], others=[c[1]["key"] for c in cands[1:]])
        for wt2, _ in cands[1:]:
            sh(f"git worktree remove --force {shlex.quote(str(wt2))}", self.repo)
        if not g["spec"]["ok"] or not g["orig"]["ok"]:
            g2 = self.fix(wt, g, "Some required tests still fail.")
            if g2["key"] > g["key"]:
                g = g2
        for rnd in range(1, self.adv_rounds + 1):
            if self.left() < self.budget * 0.12:
                break
            before = sh("git rev-parse HEAD", wt)[1].strip()
            g_adv = self.adversarial(wt, reqs, rnd)
            if g_adv["adv"]["failing"]:
                drop = self.judge(wt, g_adv["adv"]["failing"], ADV_TEST)
                self.drop_tests(wt, ADV_TEST, drop)
                self.commit(wt, "heartgold: drop wrong adversarial tests")
                g_adv = self.gate(wt)
                if g_adv["adv"]["failing"]:
                    g_adv = self.fix(wt, g_adv, "A hostile reviewer found these bugs.")
            if not g_adv["orig"]["ok"]:
                sh(f"git reset -q --hard {before}", wt)
                g = self.gate(wt)
            else:
                g = g_adv
        if self.left() > self.budget * 0.08:
            g = self.optimize(wt, g)
        # merge winner only if it does not break the original tests and beats the baseline
        final = sh("git rev-parse HEAD", wt)[1].strip()
        keep = g["orig"]["ok"] and g["key"][1] >= base["key"][1]
        if keep:
            code, out = sh(f"git merge -q --ff-only {final}", self.repo)
            if code != 0:
                code, out = sh(f"git checkout -q {final} -- . && git -c user.email=rf@rf -c user.name=heartgold commit -qam 'heartgold: apply winner'", self.repo)
            if code != 0:
                keep = False
                self.log("merge_failed", detail=out[-500:])
        sh(f"git worktree remove --force {shlex.quote(str(wt))}", self.repo)
        self.log("done", kept=keep, key=g["key"], bench=g["bench"])
        self.report(reqs, base, g, keep)
        print(f"HEARTGOLD_COST_USD={COST['usd']:.4f}")
        return keep

    def report(self, reqs, base, g, keep):
        lines = [f"# heartgold report — {datetime.datetime.now():%Y-%m-%d %H:%M}", "", f"Goal: {self.goal.strip()}", "",
                 f"Result: {'merged' if keep else 'NOT merged'} · cost ${COST['usd']:.2f}", "",
                 f"- original tests: {'pass' if g['orig']['ok'] else 'FAIL'}",
                 f"- spec tests passed: {g['spec']['passed']} · adversarial tests passed: {g['adv']['passed']}",
                 f"- bench: {base['bench']} -> {g['bench']}", "", "## Requirements", ""]
        for r in reqs:
            src = f" — [{r['url']}]({r['url']}): \"{r['quote']}\"" if r.get("verified") else " — (unsourced)"
            lines.append(f"- **{r.get('id')}** {r.get('text')}{src}")
        (self.state / "report.md").write_text("\n".join(lines) + "\n")
