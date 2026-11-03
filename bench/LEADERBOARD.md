# Leaderboard

Same model (sonnet) and per-fixture budget for every tool; tools run in a sandbox that
cannot read hidden tests. Hard suites: score = share of the gap from the naive code to the oracle closed.
DQ = read hidden test data (scored 0). '-' = no valid run yet.

## hard2 suite

| tool | score | graphemes | idna | linebreak | cost | time |
|---|---|---|---|---|---|---|
| noop | **0.535** | 0.719 | 0.226 | 0.660 | $0.00 | 0m |

## hard suite

| tool | score | cron | gitignore | pep440 | robots | urljoin | cost | time |
|---|---|---|---|---|---|---|---|---|
| plain-claude | **0.999** | 0.996 | 1.000 | 1.000 | 1.000 | 1.000 | $2.05 | 16m |
| autoresearch | **0.799** | 0.996 | DQ | 1.000 | 1.000 | 1.000 | $3.21 | 25m |
| heartgold-v1 | **0.599** | 0.996 | 1.000 | 1.000 | - | - | $4.62 | 37m |
| noop | **0.508** | 0.140 | 0.865 | 0.206 | 0.854 | 0.474 | $0.00 | 0m |

## easy suite

| tool | score | csvparse | dedupe | fuzzy | lru | ratelimit | semver | cost | time |
|---|---|---|---|---|---|---|---|---|---|
| plain-claude | **1.000** | 1.000 | 0.999 | 1.000 | 1.000 | 1.000 | 1.000 | $1.40 | 11m |
| autoresearch | **0.983** | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.900 | $2.44 | 17m |
| noop | **0.355** | 0.200 | 0.454 | 0.362 | 0.457 | 0.460 | 0.200 | $0.00 | 0m |
| heartgold-v1 | **0.317** | 1.000 | - | - | - | - | 0.900 | $2.50 | 24m |

