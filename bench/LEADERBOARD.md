# Leaderboard

Same model (sonnet) and per-fixture budget for every tool; tools run in a sandbox that
cannot read hidden tests. Hard suites: score = share of the gap from the naive code to the oracle closed.
Speed suite: score = log10(speedup on a HIDDEN benchmark)/2 x (share of hidden results correct)^10;
1.0 = 100x faster, 1.5 = 1000x. Timings re-measured one at a time on an idle machine.
DQ = read hidden test data (scored 0). '-' = no valid run yet.

## speed suite

| tool | score | fuzzymatch | lcs | nqueens | primes | cost | time |
|---|---|---|---|---|---|---|---|
| heartgold-v4 | **1.156** | 0.564 | 1.403 | 0.899 | 1.758 | $8.25 | 46m |
| plain-claude | **1.084** | 0.559 | 0.985 | 1.013 | 1.779 | $2.07 | 21m |
| heartgold-v3 | **1.081** | 0.604 | 1.569 | 1.014 | 1.135 | $8.05 | 74m |
| heartgold-v6 | **0.901** | 0.453 | 0.361 | 0.895 | 1.895 | $9.90 | 73m |
| heartgold-v5 | **0.857** | 0.716 | 0.362 | 0.593 | 1.758 | $8.64 | 55m |
| heartgold-v7 | **0.852** | 0.551 | 0.337 | 0.868 | 1.651 | $10.43 | 76m |
| autoresearch | **0.820** | 0.399 | 1.480 | 1.013 | 0.387 | $3.55 | 37m |
| heartgold-v2 | **0.626** | 0.000 | 0.519 | 0.111 | 1.876 | $5.40 | 68m |
| noop | **0.000** | 0.000 | 0.000 | 0.000 | 0.000 | $0.00 | 0m |

## hard2 suite

| tool | score | graphemes | idna | linebreak | cost | time |
|---|---|---|---|---|---|---|
| plain-claude | **1.000** | 1.000 | 1.000 | 1.000 | $4.08 | 31m |
| noop | **0.535** | 0.719 | 0.226 | 0.660 | $0.00 | 0m |

## hard suite

| tool | score | cron | gitignore | pep440 | robots | urljoin | cost | time |
|---|---|---|---|---|---|---|---|---|
| plain-claude | **0.999** | 0.996 | 1.000 | 1.000 | 1.000 | 1.000 | $2.05 | 16m |
| autoresearch | **0.799** | 0.996 | DQ | 1.000 | 1.000 | 1.000 | $3.21 | 25m |
| heartgold-v1 | **0.599** | 0.996 | 1.000 | 1.000 | - | - | $4.62 | 37m |
| noop | **0.508** | 0.140 | 0.865 | 0.206 | 0.854 | 0.474 | $0.00 | 0m |
| heartgold-v2 | **0.200** | - | - | - | - | 1.000 | $2.73 | 18m |

## easy suite

| tool | score | csvparse | dedupe | fuzzy | lru | ratelimit | semver | cost | time |
|---|---|---|---|---|---|---|---|---|---|
| plain-claude | **1.000** | 1.000 | 0.999 | 1.000 | 1.000 | 1.000 | 1.000 | $1.40 | 11m |
| autoresearch | **0.983** | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.900 | $2.44 | 17m |
| noop | **0.355** | 0.200 | 0.454 | 0.362 | 0.457 | 0.460 | 0.200 | $0.00 | 0m |
| heartgold-v1 | **0.317** | 1.000 | - | - | - | - | 0.900 | $2.50 | 24m |

