# Improvement loop protocol

Each iteration (one at a time, never two bench runs of heartgold at once):

1. If a bench run is in progress, wait for it (do not start another).
2. Read the newest `bench/results/hard-heartgold*.json` + `.heartgold/ledger.jsonl` in each
   fixture's work dir: which hidden cases fail, and at which pipeline stage it went wrong
   (research missed the rule? spec fetch failed? candidates agreed on a wrong answer? judge wrong?
   fix round reverted?). Group failures by CATEGORY, never by individual hidden case.
3. `/searchify` round: research how other systems handle that failure category.
   If the previous iteration brought NO improvement, this step is mandatory and wider: a
   `/searchify` web round plus a GitHub round (`gh search repos` / `gh search code` for the
   strongest open-source implementations of the weak spot, read their code) before any change.
4. Change heartgold (never the fixtures, never tuned to hidden-case content).
5. Re-run: `.venv/bin/python bench/run.py --tool heartgold --suite hard --label heartgold-vN`
   then `bench/leaderboard.py`, commit with the numbers in the message.
6. Stop when heartgold leads plain-claude and autoresearch on the hard suite total AND on
   every hard fixture, in 2 consecutive runs; then confirm the easy suite is still >= 0.98.

Inside heartgold itself the same rule holds: a round with no improvement triggers a web + GitHub
research round that seeds the next round of attempts.

Current target: the speed suite (correctness suites are saturated by plain-claude at 1.000).

Fairness rules: same model (sonnet) and the same per-fixture budget for every tool; if
heartgold's budget is raised, re-run competitors at that budget too.
