# Leaderboard

Same model (sonnet) and per-fixture budget for every tool; tools run in a sandbox that
cannot read hidden tests. Hard suites: score = share of the gap from the naive code to the oracle closed.
Speed suite: score = log10(speedup on a HIDDEN benchmark)/2 x (share of hidden results correct)^10;
1.0 = 100x faster, 1.5 = 1000x. Timings re-measured one at a time on an idle machine.
DQ = read hidden test data (scored 0). '-' = no valid run yet.

## speed suite

| tool | score | fuzzymatch | lcs | nqueens | primes | cost | time |
|---|---|---|---|---|---|---|---|
| heartgold-v18 | **1.286** | 0.791 | 1.489 | 0.992 | 1.871 | $10.54 | 77m |
| heartgold-v10 | **1.252** | 0.577 | 1.533 | 0.995 | 1.902 | $11.62 | 74m |
| heartgold-v4 | **1.156** | 0.564 | 1.403 | 0.899 | 1.758 | $8.25 | 46m |
| heartgold-v3 | **1.081** | 0.604 | 1.569 | 1.014 | 1.135 | $8.05 | 74m |
| heartgold-v8 | **1.065** | 0.196 | 1.433 | 0.882 | 1.751 | $7.83 | 57m |
| heartgold-v11 | **1.056** | 0.454 | 1.316 | 0.801 | 1.654 | $10.56 | 86m |
| heartgold-v12 | **1.043** | 0.377 | 1.370 | 0.786 | 1.640 | $11.15 | 82m |
| heartgold-v13 | **1.010** | 0.378 | 1.254 | 0.782 | 1.625 | $14.14 | 60m |
| heartgold-v9 | **0.926** | 0.699 | 0.116 | 1.022 | 1.867 | $11.64 | 77m |
| plain-claude | **0.901** | 0.426 | 0.753 | 0.779 | 1.647 | $1.56 | 18m |
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

## speed suite - average over repeated runs

| tool | runs | mean | fuzzymatch | lcs | nqueens | primes | per-run totals |
|---|---|---|---|---|---|---|---|
| heartgold v18 | 1 | **1.286** | 0.791 | 1.489 | 0.992 | 1.871 | 1.286 |
| heartgold (v10-v12) | 3 | **1.117** | 0.469 | 1.406 | 0.861 | 1.732 | 1.252, 1.056, 1.043 |
| plain-claude | 3 | **0.978** | 0.374 | 0.997 | 0.853 | 1.690 | 1.084, 0.950, 0.901 |

