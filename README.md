<p align="center">
  <img src="assets/heartgold-logo.png" alt="heartgold" width="220">
</p>

<h1 align="center">heartgold</h1>

<p align="center">Point it at a repo and a goal. It researches how the best people solve that problem, tries several
implementations in isolated git worktrees, and keeps only the changes it can prove are better.</p>

---

## What it does

```bash
python -m heartgold run path/to/repo --goal "Make lcs_length as fast as possible without changing its results"
```

heartgold has two modes, picked from the goal:

**Speed mode** (the goal asks for speed, and the repo has a `bench.py`):

1. **Identical-output oracle.** It writes a few hundred probe inputs and records what the *original* code returns.
   Every candidate must match those results exactly. Wrong-but-fast code is never kept.
2. **Independent benchmarks.** It writes its own second benchmark with different inputs and parameter ranges, plus
   adversarial worst-case benchmarks aimed at the current winner (RAISE-style minimax). A change must hold up on
   all of them, not just the repo's own `bench.py`.
3. **Research.** It runs web research (via a `searchify` CLI, when installed) and GitHub code search
   (`gh search code`) for the fastest known algorithms, and turns the results into ranked ideas with sources.
4. **Rounds of attempts.** Each round, coding agents try different ideas in parallel in separate git worktrees,
   starting from the current best. The fastest verified attempt wins and is merged at once.
5. **Recovery.** Attempts that are fast but wrong get a repair round that shows exactly which inputs differ. Good
   ideas that were implemented badly get a retry with reference implementations. When a round brings no gain, a
   fresh web + GitHub research round feeds the next one.

**Spec mode** (any other goal): it researches the requirements with verbatim-quote citation checks, fetches the full
specification text, writes tests from it, builds several candidates, finds inputs where they disagree, and has a
spec-reading judge settle each disagreement into an exact-value test (DiffSpec-style).

Every step is logged to `.heartgold/ledger.jsonl` in the target repo, and a `.heartgold/report.md` lists what was
tried, what was kept and why.

## Benchmarks

Everything is reproducible with `bench/run.py`. Tools run in a macOS sandbox that cannot read the hidden tests, and
every tool gets the same model (Sonnet) and the same $3 budget per fixture.

**Speed suite**: 4 repos (LCS, prime counting, fuzzy word matching, N-queens). Score = log10(speedup on a *hidden*
benchmark with different inputs) / 2, multiplied by (share of hidden results that are correct)^10. So 1.0 means
100x faster, 1.5 means 1,000x, and broken results score close to zero. All timings are re-measured one at a time
on an idle machine.

| tool | runs | mean | fuzzymatch | lcs | nqueens | primes |
|---|---|---|---|---|---|---|
| **heartgold** | 3 | **1.117** | **0.469** | **1.406** | **0.861** | **1.732** |
| plain `claude -p` (one prompt) | 3 | 0.978 | 0.374 | 0.997 | 0.853 | 1.690 |
| [autoresearch](https://github.com/uditgoenka/autoresearch) | 1 | 0.820 | 0.399 | 1.480 | 1.013 | 0.387 |

heartgold is ahead on the average of every fixture, and its worst run (1.043) beats plain Claude's average. The
N-queens gap is within run-to-run noise. It uses about 5x the tokens of a single prompt.

**Correctness suites** (spec tasks with hidden tests from real oracles: PEP 440, cron, gitignore, robots.txt,
RFC 3986, Unicode 16 grapheme and line breaking, IDNA): a single strong prompt already scores about 100%, so these
suites cannot separate good tools. They are kept as regression checks.

Full tables: [`bench/LEADERBOARD.md`](bench/LEADERBOARD.md). How the loop that built heartgold worked:
[`LOOP.md`](LOOP.md) and [`PLAN.md`](PLAN.md).

## Requirements

- Python 3.11+ with `pytest` (and `pytest-timeout`) in the environment that runs the target repo's tests
- [Claude Code](https://claude.com/claude-code) CLI (`claude -p`) - the coding agent
- Optional: a `searchify` CLI for web research, and an authenticated `gh` for GitHub code search

## Options

```
python -m heartgold run REPO --goal "..." | --goal-file goal.md
    --budget-usd 3.0       total agent spend for the run
    --time-limit 1500      wall-clock seconds
    --model sonnet
    --test-cmd / --bench-cmd   override auto-detection
```

## Status

Research prototype. The speed pipeline is the version with the best benchmark results (v10); see the git log for
what each version changed and why.
