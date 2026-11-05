<p align="center">
  <img src="assets/heartgold-logo-animated.gif" alt="heartgold - a pumping golden heart" width="220">
</p>

<h1 align="center">heartgold</h1>

<p align="center">Point it at a repo and a goal. It researches how the best people solve that problem, tries several
implementations in isolated git worktrees, and keeps only the changes it can prove are better.</p>

<p align="center">
  <i>"In the streets of Philly where n—— don't even get to turn old<br>
  My heart pumping 'til it turn gold"</i><br>
  — Meek Mill, <i>Classic Freestyle Pt. 2</i>, as heard on Knxwledge's <b>sameolemeek_</b>
</p>

<p align="center">
  🎧 Listen: <a href="https://knxwledge.bandcamp.com/track/sameolemeek">Bandcamp</a> ·
  <a href="https://open.spotify.com/track/0CUJEDKDLddR0cojCVsXN1">Spotify</a> ·
  <a href="https://genius.com/Knxwledge-sameolemeek-lyrics">Lyrics</a>
</p>

<p align="center">The name and the golden heart come from this track: a heart that keeps pumping until it turns gold.
heartgold does the same to a codebase: it keeps beating, round after round, until the code is gold.</p>

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
| **heartgold v18** (current) | 1 | **1.286** | **0.777** | **1.495** | 0.995 | **1.862** |
| heartgold v10-v12 | 3 | 1.117 | 0.469 | 1.406 | 0.861 | 1.732 |
| plain `claude -p` (one prompt) | 3 | 0.978 | 0.374 | 0.997 | 0.853 | 1.690 |
| [autoresearch](https://github.com/uditgoenka/autoresearch) | 1 | 0.820 | 0.399 | 1.480 | 1.013 | 0.387 |

heartgold is ahead on the average of every fixture, and its worst run (1.043) beats plain Claude's average. The
N-queens gap is within run-to-run noise. It uses about 5x the tokens of a single prompt.

**Correctness suites** (spec tasks with hidden tests from real oracles: PEP 440, cron, gitignore, robots.txt,
RFC 3986, Unicode 16 grapheme and line breaking, IDNA): a single strong prompt already scores about 100%, so these
suites cannot separate good tools. They are kept as regression checks.

Full tables: [`bench/LEADERBOARD.md`](bench/LEADERBOARD.md). How the loop that built heartgold worked:
[`LOOP.md`](LOOP.md) and [`PLAN.md`](PLAN.md).

## Install as a Claude Code plugin

heartgold ships as a Claude Code plugin marketplace from this repo, so you can install it straight from GitHub:

```
/plugin marketplace add Malek1414/heartgold
/plugin install heartgold@heartgold
```

This gives you:
- a `heartgold` **skill** that Claude Code can invoke automatically when you ask it to e.g. "make this faster
  without changing results" or "implement X to spec with proof", or that you can call explicitly with
  `/heartgold:heartgold`;
- a `/heartgold` **slash command** that runs `python -m heartgold run <repo> --goal "$ARGUMENTS"` for you.

heartgold's Python package has no third-party dependencies, but it still needs the [Claude Code](https://claude.com/claude-code)
CLI (`claude`) on `PATH` to run its headless coding agent, plus `pytest`/`pytest-timeout` in the environment
that runs your target repo's tests. `gh` and `searchify` are optional research sources. See the skill's
`SKILL.md` for the full setup and how to read `.heartgold/report.md` and `.heartgold/ledger.jsonl` afterward.

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

Research prototype. The current pipeline (v18) has the best speed-suite score so far (1.286) and is the first
version that improved a real codebase: on [Neurotree](bench/real/README.md) (a 55k-node, 160 MB graph) it made
`attend()` 4.5x faster with identical results and all 36 tests passing. Each real-repo run so far exposed a bug the
small fixtures could not (see bench/real/README.md); more real repos are next. The git log explains what each
version changed and why.
