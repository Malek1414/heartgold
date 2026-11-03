import argparse, pathlib, sys

from .core import Run


def main():
    ap = argparse.ArgumentParser(prog="repoforge")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="research, implement, verify and merge an improvement")
    r.add_argument("repo", nargs="?", default=".")
    r.add_argument("--goal")
    r.add_argument("--goal-file")
    r.add_argument("--budget-usd", type=float, default=3.0)
    r.add_argument("--model", default="sonnet")
    r.add_argument("--candidates", type=int, default=2)
    r.add_argument("--adversarial-rounds", type=int, default=2)
    r.add_argument("--test-cmd")
    r.add_argument("--bench-cmd")
    a = ap.parse_args()
    goal = a.goal or (pathlib.Path(a.repo) / a.goal_file).read_text() if a.goal_file else a.goal
    if not goal:
        sys.exit("give --goal or --goal-file")
    ok = Run(a.repo, goal, a.model, a.budget_usd, a.candidates, a.adversarial_rounds, a.test_cmd, a.bench_cmd).run()
    sys.exit(0 if ok else 1)


main()
