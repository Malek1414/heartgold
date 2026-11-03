# heartgold — implementation plan

Goal: a CLI that takes any git repo plus a goal, researches the web for how to do it
well, implements candidate changes in isolation, and keeps only what is proven better.
Success = beat the top GitHub tools for this (uditgoenka/autoresearch, evolution-kernel)
on one shared benchmark, same budget.

## 1. Benchmark first (the yardstick) — `bench/`

Fixture repos in `bench/fixtures/<name>/`:
- `repo/`   the code the tool sees (src, visible tests, `goal.md`, `bench.py`)
- `hidden/` held-out tests the tool never sees (spec edge cases, regressions)

Fixtures need real research nuance (a spec or known algorithm the naive code misses):
1. `semver`    – precedence wrong on prereleases → SemVer 2.0.0 §11
2. `csvparse`  – breaks on quoted fields → RFC 4180
3. `ratelimit` – fixed window allows 2x burst at boundary → sliding window / token bucket
4. `lru`       – O(n) eviction, no TTL → O(1) LRU + TTL
5. `fuzzy`     – Levenshtein misses transpositions, slow → Damerau (OSA) + speed
6. `dedupe`    – O(n²) order-preserving dedupe, slow sort helpers → speed, stability

Runner `bench/run.py --tool <adapter> [--fixtures ...] [--budget-usd N]`:
copy fixture → temp dir → `git init` → run tool → score:
- hidden pass rate (main metric)
- visible pass rate (must stay 100%, else regression)
- speedup on `bench.py` (when the goal is about speed)
- false keep = a change was kept but hidden pass went down
- wall time, cost (from `claude -p --output-format json`)
Composite = 70% hidden + 20% speed (capped 10x, log scale) + 10% clean (no regressions).
Results → `bench/results/<tool>-<timestamp>.json` and `bench/LEADERBOARD.md`.

Adapters in `bench/adapters/`: `noop` (baseline), `heartgold`, `autoresearch`
(uditgoenka skill via `claude -p`), `evolution-kernel`, `plain-claude` (one
`claude -p` with the goal: the strong control every loop must beat).

## 2. heartgold v1 — `heartgold/`

Pipeline per run, each phase writes to `.heartgold/` in the target repo:
1. **map**: detect language, test cmd, bench cmd; run baseline; write `map.json`.
2. **research**: turn goal + repo map into 3–5 queries; `searchify passages` +
   GitHub search for similar code; save sources with verbatim quotes.
3. **verify citations**: re-fetch each source; drop proposals whose quote
   is not on the page (no hallucinated "the spec says").
4. **propose**: agent writes N ranked proposals with a cited claim and the
   *test it would add* to prove it (proposal = hypothesis + falsifier).
5. **implement**: each proposal in its own git worktree via `claude -p`.
6. **gate**: visible tests 100%, new proposal tests pass, bench not worse,
   new tests pass on new code AND fail on old code (proves the test is real),
   secret scan. Keep winners, roll back the rest.
7. **merge**: apply winners one by one, re-gate after each merge.
8. **ledger**: append-only `ledger.jsonl` of every attempt, source, score;
   next cycle reads it (no repeating failed ideas).

Repeat cycles until no proposal improves the score or the budget runs out.

## 3. Loop (until it wins)

Each iteration:
1. run bench for heartgold (+ competitors when they change)
2. read the failures (which hidden tests, why)
3. research round with `/searchify`: how do others fix this weakness
4. change heartgold (not the fixtures; fixtures are frozen once v1 lands, new
   fixtures may be added but every tool is re-run on them)
5. re-run the bench, update LEADERBOARD.md, commit

Stop when heartgold leads every metric over every competitor on the full
fixture set, across 2 consecutive runs (to rule out luck).

## Rules
- Hidden tests are never readable by any tool (copied in only after the run).
- Same model (sonnet) and same budget for every tool.
- Never tune heartgold on the hidden tests' content; only on failure categories.
