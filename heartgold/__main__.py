import argparse, pathlib, re, sys

from .core import SPEED_WORDS, Run, SpeedRun


def main():
    ap = argparse.ArgumentParser(prog="heartgold")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="research, implement, verify and merge an improvement")
    r.add_argument("repo", nargs="?", default=".")
    r.add_argument("--goal")
    r.add_argument("--goal-file")
    r.add_argument("--budget-usd", type=float, default=3.0)
    r.add_argument("--model", default="sonnet")
    r.add_argument("--candidates", type=int, default=3)
    r.add_argument("--diff-rounds", type=int, default=2)
    r.add_argument("--time-limit", type=int, default=1500, help="seconds of wall clock for the whole run")
    r.add_argument("--test-cmd")
    r.add_argument("--bench-cmd")
    r.add_argument("--metric-cmd", help="metric mode: prints the score on tuning data as JSON (last line)")
    r.add_argument("--holdout-cmd", help="metric mode: the same score on held-out data (run with HEARTGOLD_HOLDOUT=1)")
    r.add_argument("--metric", default="P@1", help="metric mode: the key to raise")
    r.add_argument("--also", action="append", default=[], help="metric mode: further keys (tie-break; must not drop on held-out)")
    r.add_argument("--protect", action="append", default=[], help="metric mode: files restored before every score (the metric code)")
    r.add_argument("--rounds", type=int, default=3)
    a = ap.parse_args()
    goal = a.goal or (pathlib.Path(a.repo) / a.goal_file).read_text() if a.goal_file else a.goal
    if not goal:
        sys.exit("give --goal or --goal-file")
    if a.metric_cmd:
        if not a.holdout_cmd:
            sys.exit("metric mode needs --holdout-cmd: a score on tuning data alone proves nothing")
        from .metric import MetricRun
        ok = MetricRun(a.repo, goal, a.metric_cmd, a.holdout_cmd, a.metric, a.also, a.protect, a.rounds, model=a.model,
                       budget=a.budget_usd, candidates=a.candidates, diff_rounds=a.diff_rounds, test_cmd=a.test_cmd,
                       bench_cmd=a.bench_cmd, time_limit=a.time_limit).run()
        sys.exit(0 if ok else 1)
    cls = SpeedRun if (SPEED_WORDS.search(goal) and (pathlib.Path(a.repo) / "bench.py").exists()
                       and re.search(r"(only goal|as fast as possible)", goal, re.I)) else Run
    ok = cls(a.repo, goal, a.model, a.budget_usd, a.candidates, a.diff_rounds, a.test_cmd, a.bench_cmd, a.time_limit).run()
    sys.exit(0 if ok else 1)


main()
