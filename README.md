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

**Metric mode** (give `--metric-cmd` and `--holdout-cmd`): for scores rather than speed (accuracy, recall, nDCG). The
repo prints its score as JSON on data the agents may tune on, and on held-out data that only heartgold may read
(`HEARTGOLD_HOLDOUT=1` is set for that one command and never for an agent). Attempts run in parallel worktrees and
are chosen on tune data; tests and the metric code itself are restored before every score; a change that makes the
held-out score worse is dropped as overfitting. The report quotes the held-out change with a paired-bootstrap 95 %
interval, the only number worth quoting.

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

## Languages

heartgold works in the repo's own language. Each ecosystem has an adapter (`heartgold/lang.py`) that knows how to run
the repo's tests and heartgold's own tests separately, read the results, where heartgold's tests and probe programs
go, and how to run an extra benchmark. `tests/test_lang.py` builds a real project in every language and checks all of
it against the real toolchain.

| Language | Tests | Adapter checked on a real project | Full run with agents |
|---|---|---|---|
| Python | pytest | yes | speed, spec and metric suites; Neurotree |
| JavaScript / TypeScript | node:test, vitest, jest | yes | speed: LCS 62x (80x on unseen inputs, 3,004 unseen cases identical) |
| Rust | cargo test | yes | speed: prime counting 405x (606x at an unseen size, 2,406 unseen cases identical) |
| Go | go test | yes | spec: SemVer 2.0.0 precedence from an empty stub, passes 153 hidden checks |
| Java | JUnit 5 via Maven | yes | not yet |
| Ruby | RSpec | yes | not yet |
| C# | xUnit via `dotnet test` | yes | not yet |
| C / C++ | CTest via CMake | yes | not yet |
| PHP | PHPUnit | yes | not yet |
| Swift | XCTest | no (needs full Xcode) | not yet |

The probe protocol is the same everywhere: a small program that calls the public API on hundreds of inputs and
prints one JSON array (`"=<result as JSON>"` or `"!<error type>"` per case). heartgold records it against the original
code and every candidate must match it. Speed mode also writes its independent and adversarial benchmarks in the
repo's language.

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

- Python 3.11+ to run heartgold itself (no third-party dependencies)
- The target repo's own toolchain: pytest, node, cargo, go, maven, rspec, dotnet, cmake or phpunit
- [Claude Code](https://claude.com/claude-code) CLI (`claude -p`) - the coding agent
- Optional: a `searchify` CLI for web research, and an authenticated `gh` for GitHub code search

## Options

```
python -m heartgold run REPO --goal "..." | --goal-file goal.md
    --budget-usd 3.0       total agent spend for the run
    --time-limit 1500      wall-clock seconds
    --model sonnet
    --test-cmd / --bench-cmd   override auto-detection

metric mode:
    --metric-cmd "..."     prints the score on tuning data as JSON (last line)
    --holdout-cmd "..."    the same on held-out data; run only by heartgold, with HEARTGOLD_HOLDOUT=1
    --metric P@1           the key to raise;  --also nDCG@10  keys that must not drop on held-out data
    --protect FILE         files restored before every score (the metric code)
    --rounds 3
```

## Status

Research prototype. Results on real code, each checked independently afterwards:

- **Neurotree, speed** ([bench/real](bench/real/README.md)): `attend()` 4.5x faster (0.362 s → 0.080 s) with
  identical results and 36/36 tests.
- **Neurotree, accuracy** (metric mode): held-out P@1 0.55 → 0.60 and nDCG@10 0.169 → 0.195 on 40 questions no agent
  ever saw, on frozen inputs. The paired bootstrap for P@1 is +0.050 [+0.000, +0.125], so a likely gain rather than a
  proven one. It kept one change (reciprocal rank fusion) out of nine tried. One of the others raised the tune score
  but lowered the held-out score, and the held-out gate dropped it.
- **JavaScript, speed**: LCS 62x faster. On 3,004 inputs it never saw the results were identical, and on an unseen
  input distribution it was 80x faster. Cost $0.87.
- **Rust, speed**: prime counting 405x faster. 2,406 unseen inputs were identical, and at an unseen size (n = 5M) it
  was 606x faster. Cost $2.73.
- **Go, spec**: SemVer 2.0.0 precedence from an empty stub. It wrote spec tests in Go and ran a 90-case Go probe
  across three candidates, and the result passes 153 hidden checks. Cost $1.17.

Logs of every run are in `bench/results/`. The git log explains what each version changed and why.

## License and attribution

heartgold is created by **Malek Hassan** ([@Malek1414](https://github.com/Malek1414)) and licensed under the
[Apache License 2.0](LICENSE). Under section 4 of the license, every copy, fork or derivative work that is
redistributed must keep the [NOTICE](NOTICE) file, the copyright and attribution notices in the source files, and a
statement of the changes it makes.
