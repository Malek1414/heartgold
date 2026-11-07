# Copyright 2026 Malek Hassan (https://github.com/Malek1414/heartgold)
# SPDX-License-Identifier: Apache-2.0
"""Metric mode: raise a measured score (accuracy, recall, nDCG...) and keep only what holds up on held-out data.

The repo supplies two commands that print one JSON object on their last line:
  --metric-cmd    the score on the data agents may tune on (they run it themselves while they work)
  --holdout-cmd   the same score on held-out data. heartgold runs it with HEARTGOLD_HOLDOUT=1 in the environment of
                  that one command; agents never get the variable, so a repo can refuse to print held-out numbers to
                  them. The JSON may carry "per_question": {metric: [scores in a fixed order]} for paired bootstraps.

Each round, coding agents implement different ideas in parallel git worktrees, starting from the current best. A
candidate is kept only if (1) the repo's tests pass with the original tests and the protected files (the metric
code itself) restored from the baseline, (2) it beats the current best on the tune data by more than the noise
floor, and (3) it does not make the held-out score worse than the baseline. Candidates are chosen on tune data
only; held-out is a gate, never a target. The final report gives the held-out change with a paired bootstrap
interval, which is the number to quote.
"""
from __future__ import annotations

import json, os, random, shlex, threading
from concurrent.futures import ThreadPoolExecutor

from .agent import COST, LAST, claude, extract_json
from .core import Run, sh

_MEASURE = threading.Lock()


def last_json(out: str) -> dict | None:
    for line in reversed(out.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


def paired_bootstrap(a: list, b: list, n: int = 4000, seed: int = 7) -> tuple[float, float, float]:
    """Mean of b - a and its 95 % interval, resampling questions."""
    if not a or len(a) != len(b):
        return 0.0, 0.0, 0.0
    d = [y - x for x, y in zip(a, b)]
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return sum(d) / len(d), means[int(0.025 * n)], means[int(0.975 * n)]


class MetricRun(Run):
    def __init__(self, repo, goal, metric_cmd, holdout_cmd, metric="P@1", also=None, protect=(), rounds=3,
                 min_gain=0.01, **kw):
        super().__init__(repo, goal, **kw)
        self.metric_cmd, self.holdout_cmd = metric_cmd, holdout_cmd
        self.metric, self.also = metric, list(also or [])
        self.protect, self.rounds, self.min_gain = list(protect), rounds, min_gain

    # ---------- measuring
    def score(self, cwd, holdout=False) -> dict | None:
        env = {**os.environ, "HEARTGOLD_HOLDOUT": "1"} if holdout else {k: v for k, v in os.environ.items() if k != "HEARTGOLD_HOLDOUT"}
        import subprocess
        try:
            p = subprocess.run(self.holdout_cmd if holdout else self.metric_cmd, cwd=cwd, shell=True, capture_output=True,
                               text=True, timeout=1200, env=env)
            return last_json(p.stdout) if p.returncode == 0 else None
        except subprocess.TimeoutExpired:
            return None

    def objective(self, s: dict | None) -> float:
        # the primary metric, with the others as a small tie-breaker
        if not s:
            return float("-inf")
        return s.get(self.metric, 0.0) + 0.1 * sum(s.get(m, 0.0) for m in self.also)

    def measure(self, wt) -> dict:
        with _MEASURE:  # one at a time: the evaluation is CPU-bound
            if self.protect or self.orig_tests:
                sh(f"git checkout {self.base} -- " + " ".join(map(shlex.quote, self.protect + self.orig_tests)), wt)
            t = self.tests(wt, " ".join(map(shlex.quote, self.orig_tests))) if self.orig_tests else dict(ok=True, failing=[], tail="")
            tune = self.score(wt)
            return dict(tests=t["ok"], failing=t.get("failing", []), tail=t.get("tail", ""), tune=tune, obj=self.objective(tune))

    def show(self, s):
        return ", ".join(f"{k} {s[k]:.3f}" for k in [self.metric, *self.also] if s and k in s) if s else "no score"

    # ---------- ideas
    def ideas(self, best, history, retry=False):
        tried = "\n".join(f"- {h}" for h in history[-16:]) or "(nothing yet)"
        reply = claude(
            f"Goal:\n{self.goal}\n\nCode:\n{self.code}\n\nCurrent score on the tuning data (`{self.metric_cmd}`): "
            f"{self.show(best['tune'])}.\n\nAlready tried:\n{tried}\n\n"
            "Research how the best systems solve this kind of problem (you may search the web and read papers), then "
            "list the 6 most promising, DIFFERENT changes to the code that would raise the score on NEW data, not just "
            "on the tuning data: better models or features, better ranking or fusion, fixing systematic errors you can "
            "find by reading the code. No per-example special cases, no hard-coded answers, no lookups of the "
            "evaluation data. For each: name, how it works, why it should generalise, expected gain. Reply only with "
            'JSON: {"ideas": [{"name": "...", "how": "...", "why": "...", "expected_gain": 0.05, "source": "url or null"}]}',
            str(self.repo), self.model, self.slice(0.05), timeout=900, tools=["Read", "Grep", "Glob", "WebSearch", "WebFetch"])
        ideas = (extract_json(reply, {}) or {}).get("ideas") or []
        if not ideas and not retry:
            # an empty or unparseable reply (e.g. the prompt grew too long with history): once more, with less code
            self.log("metric.ideas_retry", reply=(reply or "")[:300])
            code, self.code = self.code, self.code[:20000]
            try:
                return self.ideas(best, history, retry=True)
            finally:
                self.code = code
        self.log("metric.ideas", ideas=[i.get("name") for i in ideas])
        return ideas

    def attempt(self, i, ref, idea, best):
        wt = self.worktree(f"metric{i}", ref)
        claude(
            f"Goal:\n{self.goal}\n\nCurrent score on the tuning data: {self.show(best['tune'])}. Measure with: "
            f"`{self.metric_cmd}` (prints JSON; takes a while, so think before you run it).\n\n"
            f"Change to implement now: {idea.get('name')}: {idea.get('how')}\n\n"
            "Implement it as well as you can, measure, and iterate a few times. The change must generalise to data "
            "you cannot see: heartgold scores it on held-out data too and throws it away if that gets worse. Rules: "
            f"all tests must pass ({self.test_cmd}); do not edit tests or these files: {', '.join(self.protect) or '-'}; "
            "no special cases for individual examples, no hard-coded answers, do not read or copy the evaluation "
            "questions into the code. Keep the code fast.",
            wt, self.model, self.slice(0.15, floor=0.3), timeout=1800)
        self.commit(wt, f"heartgold metric attempt: {idea.get('name')}")
        m = self.measure(wt)
        self.log("metric.attempt", i=i, idea=idea.get("name"), tests=m["tests"], obj=round(m["obj"], 4),
                 score=self.show(m["tune"]), failing=m["failing"][:6])
        return wt, m

    def run(self):
        self.detect()
        base = self.measure(self.repo)
        base_hold = self.score(self.repo, holdout=True)
        if not base["tune"] or not base_hold:
            self.log("metric.no_score", detail="the metric or held-out command printed no JSON")
            return False
        self.log("metric.baseline", tune=self.show(base["tune"]), holdout=self.show(base_hold), tests=base["tests"])
        best, best_ref, best_hold, history, accepted = base, self.base, base_hold, [], []
        for rnd in range(self.rounds):
            if self.left() < self.budget * 0.15 or self.time_limit and (__import__("time").time() - self.t0) > self.time_limit:
                break
            ideas = self.ideas(best, history)[: self.n_cand]
            if not ideas:
                break
            with ThreadPoolExecutor(len(ideas)) as ex:
                results = list(ex.map(lambda a: self.attempt(a[0], best_ref, a[1], best), enumerate(ideas)))
            round_best = None
            for (wt, m), idea in zip(results, ideas):
                gain = m["obj"] - best["obj"]
                history.append(f"{idea.get('name')}: tests {'ok' if m['tests'] else 'FAIL'}, tune {self.show(m['tune'])} ({gain:+.3f})")
                if m["tests"] and gain > self.min_gain and (round_best is None or m["obj"] > round_best[1]["obj"]):
                    round_best = (wt, m, idea)
            if round_best:
                wt, m, idea = round_best
                hold = self.score(wt, holdout=True)
                worse = not hold or any(hold.get(k, 0) < base_hold.get(k, 0) - 1e-9 for k in [self.metric, *self.also])
                self.log("metric.holdout_gate", idea=idea.get("name"), holdout=self.show(hold), kept=not worse)
                if not worse:
                    best, best_ref, best_hold = m, self.head(wt), hold
                    accepted.append(idea.get("name"))
                    history[-1] += " -> KEPT"
                else:
                    history.append(f"{idea.get('name')}: better on tune data but worse on held-out data (overfit), dropped")
            for wt, _ in results:
                if not best_ref or self.head(wt) != best_ref:
                    self.drop_worktree(wt)
            self.log("metric.round", round=rnd, best=self.show(best["tune"]), holdout=self.show(best_hold))
        if best_ref != self.base:
            sh(f"git merge --ff-only {best_ref} || git -c user.email=rf@rf -c user.name=heartgold merge --no-edit {best_ref}", self.repo)
        self.final(base, base_hold, best, best_hold, accepted)
        return best_ref != self.base

    def final(self, base, base_hold, best, best_hold, accepted):
        lines = ["# heartgold metric report", "", f"Goal: {self.goal}", "", f"Kept changes: {', '.join(accepted) or 'none'}", "",
                 "| | tune data | held-out data |", "|---|---|---|",
                 f"| baseline | {self.show(base['tune'])} | {self.show(base_hold)} |",
                 f"| heartgold | {self.show(best['tune'])} | {self.show(best_hold)} |", ""]
        bs = {}
        for k in [self.metric, *self.also]:
            a = (base_hold.get("per_question") or {}).get(k)
            b = (best_hold.get("per_question") or {}).get(k)
            if a and b:
                bs[k] = paired_bootstrap(a, b)
                d, lo, hi = bs[k]
                lines.append(f"- held-out {k}: {d:+.3f} [{lo:+.3f}, {hi:+.3f}] (paired bootstrap, 95 %, n={len(a)})")
        lines.append(f"\nCost ${COST['usd']:.2f}. Candidates were chosen on tune data only; held-out data only gated them.")
        (self.state / "report.md").write_text("\n".join(lines) + "\n")
        self.log("metric.done", tune=self.show(best["tune"]), holdout=self.show(best_hold),
                 bootstrap={k: [round(x, 3) for x in v] for k, v in bs.items()}, kept=accepted)
