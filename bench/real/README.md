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
