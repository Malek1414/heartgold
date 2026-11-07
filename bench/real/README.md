# Real-repo results

Benchmarks on small fixtures can be gamed by accident; these runs point heartgold at real code with real data.
Every result here was re-checked by hand after the run, outside heartgold.

## Neurotree (attention graph of a Mac: 55,231 nodes, 75,476 edges, 160 MB SQLite graph)

Goal: make the core of `neurotree ask` (load the graph, then `attend()` per question) faster, results identical.
Run on a clone against a frozen copy of the graph and a fixed clock. heartgold v18, budget $5, 29 minutes.

| | original | heartgold | |
|---|---|---|---|
| 12 questions, `attend()` only (best of 5 reps, 3 alternating rounds) | 0.362 s | **0.080 s** | **4.5x faster** |
| graph load (median) | 0.697 s | 0.690 s | unchanged |
| results, 33 questions x 2 clocks | | identical (max difference 0.0) | |
| Neurotree test suite | 36 pass | 36 pass | |

What it changed ([patch](neurotree-attend.patch), one file, +44/-9): `prior()` is cached on the index per
(as_of, scales) instead of recomputed for every question, and `_pct` ranks all levels in one vectorised pass instead
of a per-level loop. Review note: the prior cache is unbounded; cap it before using it in a long-running process.

What it took to get there (each a bug only real repos expose, all fixed in heartgold):
1. A 60k-character repo dump starved every agent's budget: now the agents see the cProfile hot path instead (v15).
2. Test detection handed the viewer's TypeScript tests to pytest, so every candidate (and the original) "failed" (v16).
3. Bit-exact float comparison rejected every numeric optimisation (summing in another order): now 9 significant digits (v17).
4. Two attempts timed at the same moment made every candidate look slower: measurement is now one at a time (v18).

## Neurotree accuracy (metric mode, November 2026)

Goal: rank the right project first (P@1) and rank files better (nDCG@10) on questions never seen. Inputs were
frozen: the index as of 5 Nov and 110 questions from sessions before it. Bench's own time split was used: whole
sessions, with the older 60 % (70 questions) to tune on and the newer 40 % (40) held out. Agents only saw
`python -m neurotree.evaljson --split tune`; held-out scores print only with `HEARTGOLD_HOLDOUT=1`, which heartgold
sets for its own check and never for an agent. `neurotree/evaljson.py` and `neurotree/bench.py` were restored before
every score.

| | tune P@1 | tune nDCG@10 | held-out P@1 | held-out nDCG@10 |
|---|---|---|---|---|
| before | 0.400 | 0.158 | 0.550 | 0.169 |
| after | 0.457 | 0.189 | 0.600 | 0.195 |

Held-out, paired bootstrap 95 % (n = 40): P@1 +0.050 [+0.000, +0.125], nDCG@10 +0.026 [−0.030, +0.080].

Two runs (`bench/results/metric-neurotree-r1.log`, `-r2.log`) tried nine ideas and kept one: reciprocal rank fusion
of the lexical and semantic heads, plus retuned constants. A direct project-scoring stage raised tune P@1 to 0.486
but lowered held-out P@1 to 0.575, so it was dropped as overfit. Queries became slower but stay under the 100 ms goal:
median 26 → 44 ms, p90 42 → 77 ms. Agent cost: $3.81 + $8.53. The change is merged in Neurotree with these numbers
in its `docs/attention.md`.
