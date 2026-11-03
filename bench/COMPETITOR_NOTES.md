# Competitor research for heartgold — full notes

Cloned to `scratchpad/competitors/{autoresearch,evolution-kernel,openevolve,synth-loop,Agent-Loop-Skills}`.
GitHub metadata pulled via `gh api repos/<owner>/<repo>` on 2026-11-03.

---

## 1. uditgoenka/autoresearch — 6,795 stars, 493 forks, 0 open issues (Shell/Markdown, Claude Code Skill)

**What it is:** Not a standalone CLI — a Claude Code / OpenCode / Codex / pi *Skill* (Markdown prompt + hooks) that you invoke *inside* an agent session via `/autoresearch`. Based on Karpathy's 630-line autoresearch script, generalized to any domain.

**Loop steps (classic mode):**
1. Setup: read all in-scope files, extract/ask for a mechanical metric, define scope (writable vs read-only files), run verification once for baseline (iteration 0).
2. Loop (default 25 iters, `Iterations: unlimited` opt-in): review git history + TSV results log → pick next change (informed by what worked/failed/untried) → make ONE change → `git commit` (before verifying, so last-good state is always in git) → run `Verify:` command → compare metric → **keep** (leave commit) or **discard** (`git revert`) → append TSV row → repeat.
3. Optional `Guard:` command (contributed by JetBrains, PR #7) — a second command that must *also* pass; if metric improves but guard fails, reworks up to 2 attempts. This is their only "don't regress something else" mechanism in the core loop.
4. **Fork-and-flush** (v2.3, citing arXiv:2610.07447 and arXiv:2610.07625): at 33%/66% of budget, or after 5 iterations with no `keep`, forks K fresh-context branches off the best commit, runs each briefly, keeps the winner. Half the branches are random, half get a single distinct experiment from a stateless "Advisor" that reads the results log. This is their main anti-plateau trick.
5. `/autoresearch:regression` is a separate stability gate (not part of the core loop) that captures baseline behavior in an **isolated git worktree**, diffs 8 dimensions (functional/api-contract/data-migration/integration-e2e as hard gates; flakiness/performance/resource/visual-ui as a weighted 0-100 score, threshold 95), and classifies regressions strictly as green→red (never red→red or flaky→red).

**Verify/gate:** Pure shell-command exit-code / metric-string matching. No isolation for the core loop itself — iterations mutate the working tree directly and rely on commit-then-revert. Isolation (git worktree) is reserved for the separate regression-gate subcommand only.

**Next-try selection:** The agent (an LLM) reads TSV history + git log and picks freely — no formal search algorithm, no island/population model. Fork-and-flush is the only structured exploration mechanism.

**Web research:** None in the core optimization loop. `/autoresearch:improve` does ICP/competitor/market research (web) but it's a *product-feature* discovery command, terminal in the chain — it hands off PRDs to external tools, it does not feed code-level "improvement ideas with citations" back into the metric loop. There is no citation-gated change proposal mechanism anywhere in this repo.

**Memory across iterations:** git log + git diff + a TSV results log (`iteration, commit, metric, delta, status, description`) re-read each iteration; `handoff.json` passes structured state between chained subcommands; `orchestrator-state.json` tracks the newer goal-driven orchestrator's progress. No persistent cross-run memory beyond what's committed to the repo (i.e., no external vector DB / learned prior).

**Headless invocation (confirmed from `guide/advanced-patterns.md`, used in their own CI examples):**
```bash
claude -p "/autoresearch
Iterations: 40
Goal: Increase test coverage to 90%
Scope: src/**/*.ts
Verify: npm test -- --coverage | grep 'All files'
Guard: npm run build
--evals-interval 10
--evals"
```
and `claude -p "/autoresearch:evals --format json --recommend" > evals.json`.

**Known weaknesses (from 28 closed issues, repo currently has 0 open — the maintainer closes fast):**
- Hooks are "defense-in-depth, not a security sandbox" by their own README — they're regex/path-based Node scripts, not a real jail.
- Multiple hook bugs found and fixed: `privacy-block`'s `APPROVED:` bypass didn't work (path resolved before the hook saw it); `scout-block` false-positive-blocked remote paths in ssh/scp/rsync commands; `dangerous-cmd-block` blocked legitimate `git push --force-with-lease`; `simplify-gate` miscounted binary files as LOC; hooks were silent no-ops on Windows (`/dev/stdin` ENOENT, backslash paths).
- Plugin installation had a recursive self-nesting bug causing install failures (issue #43/#35).
- No isolation in the core loop — a bad iteration literally lives in your working tree until reverted; if the agent hangs or the revert step itself is interrupted, the repo can be left dirty.
- Entirely interactive-agent-driven "pick what to try next" — no algorithmic search, so results are only as good as that session's one-shot reasoning (mitigated only by fork-and-flush).

---

## 2. Protocol-zero-0/evolution-kernel — 74 stars, 12 forks, 1 open issue (Python, ~1,900-line core)

**What it is:** The closest architectural analog to heartgold. A real Python CLI/package (`pip install evolution-kernel`) — not an in-chat skill — explicitly "self-improving code for any git repo."

**Loop steps:**
1. **Observe** — run `evidence_sources` (shell command, file, or HTTP GET) to get current metric state.
2. **Plan** — LLM (Anthropic or OpenAI) reads goal + observation + last N history reflections (default 10), emits `plan.json` (summary, steps, expected_improvement).
3. **Execute** — a coding-agent adapter (Aider or **Claude Code**) applies the plan inside an **isolated git worktree**, wrapped in a **firejail OS-level sandbox** (filesystem-only: blocks writes outside the worktree; does NOT block network, fork bombs, or process injection — stated explicitly in their "Known limitations").
4. **Evaluate** — LLM + shell re-run the metric, decide accept/reject. A separate optional `goal_evaluator` role can stop the whole run early when the mission is "won."
5. **Commit/rollback** — accept → real `git commit` onto `evolution/accepted`; reject → worktree discarded, branch kept for audit.
6. Loop until `max_iterations`, `max_consecutive_failures`, `max_total_usd`, or `max_total_tokens` fires.
7. **k-branch parallel exploration** (`parallel.k_branches`, FunSearch/AlphaEvolve-style): spawns k independent worktrees per round, scores each, promotes the best, demotes the rest to `ledger/failed/`.

**Verify/gate:** Config-pluggable shell/HTTP evidence source; acceptance decision is made by an **LLM evaluator**, not a hard mechanical gate by default — their own README flags this: "The evaluator is an LLM. It can be fooled by patches that look correct but are not... Use `goal_evaluator` + a strong programmatic gate in `evidence_sources` to anchor the LLM judgment to ground truth." They also publish a genuinely good practice: **null-model ablation** — rerun the harness with the model replaced by an empty stub; if the "improved" metric still passes, the loop gamed the metric rather than improving the agent (caught exactly this on their own Wordle-agent demo, where the loop silently swapped in a classical solver).

**Next-try selection:** LLM planner reads a short reflection history + the goal; k-branch mode adds population-style parallel exploration, but there's no feature-map/novelty mechanism (no MAP-Elites).

**Web research:** None. Goal/evidence is purely numeric (your own benchmark command or HTTP endpoint). No citation or external-improvement-idea sourcing anywhere in the kernel.

**Memory across iterations:** Full forensic ledger per run (`goal.json, observation.json, planner_input.json, plan.json, executor_input/output.json, patch.diff, candidate_commit.txt, evaluation.json, decision.json, reflection.json` per `runs/000N/`); the planner only sees the last N *one-line reflections*, not full prior plans — explicitly flagged as a limitation ("History is summary, not replay... long-horizon strategies need the planner to encode state into plan.json summaries itself").

**Headless invocation (confirmed from README):**
```bash
evolution-kernel --config evolution.yml --repo /path/to/repo --ledger /tmp/ledger --loop
```
(single round without `--loop`; `--reset` clears hard-stop state.) `evolution.yml` sets `mission`, `evidence_sources`, `mutation_scope.allowed_paths`, `hard_stops`, `llm.provider/model`, `coding_agent.tool` (`aider` or `claude-code`), `sandbox.backend: firejail`.

**Known weaknesses:**
- Headline "~85% on SWE-bench Verified" result in their README is explicitly labeled a **projected target, not measured** — the only reproducible artifacts are a 1-second $0 ruff-cleanup quickstart and 99 unit/fixture tests; there is no real end-to-end benchmark run published.
- Sandbox doesn't block network access — an executed agent could still exfiltrate data or hit paid APIs unbounded.
- Real-provider (Aider/Claude Code/Anthropic/OpenAI) integration is "tested manually before each release, not on every push" — i.e., not covered by CI.
- Single open issue is a meta/roadmap issue (in Chinese) about going from MVP to "soul plugin" — signals the project is still pre-v1.1 in ambition, small community (12 forks, no visible active discussion).
- Cost can compound fast: their own estimate is $40–$100 for a 30-round loop with Claude Sonnet + Claude Code.

---

## 3. algorithmicsuperintelligence/openevolve — 7,702 stars, 1,207 forks, 89 open issues (Python, open AlphaEvolve clone)

**Scope limited to evaluation/keep logic as requested.**

**What it is:** Not git-based and not really "improve a whole repo's tests" — it evolves a single program (or, via diffs, a scoped set of files) against a **programmatic evaluator you write**, using a MAP-Elites-style population database (islands + feature-map cells), not a simple single-lineage keep/revert.

**Evaluation/keep logic:**
- Your `evaluator.py` is loaded with `importlib`'s `spec.loader.exec_module(module)` and run **in-process** — i.e., arbitrary user code execution with no sandbox by default (flagged by open issue #481: "`evaluator` exec_module operator-supplied code in-process; `visualizer` serves checkpoint data with no auth").
- Supports **cascade evaluation**: cheap `evaluate_stage1` runs first; only candidates that clear it proceed to costlier `evaluate_stage2`/`stage3` — explicitly to avoid wasting compute on bad candidates. Bug (issue #439, open): the **novelty check currently runs after evaluation**, so it still wastes compute evaluating duplicates before discarding them — acknowledged as a "good first issue."
- Evaluation has a hard `timeout` (default from config) via `asyncio.wait_for`; timeouts are captured as structured artifacts, not silent failures.
- "Keep" is not binary accept/reject — accepted programs enter a **population database** (feature-dimension grid cells + islands for diversity); a program only replaces the occupant of its cell if it scores higher there, and the **global best is always protected** regardless of which island/cell it occupies. This is fundamentally richer than heartgold's planned single-track "keep or rollback," but also means openevolve has no notion of "the current repo state" — there's no single canonical working tree, just a database of candidate programs.
- Multi-objective support exists only informally via `combined_score`; issue #453 (open) asks for proper lexicographic multi-objective ordering — not yet implemented cleanly.

**Next-try selection:** Prompt sampler draws inspiration programs from the island/MAP-Elites database (not git history) + diff-based LLM mutation. This is evolutionary population search, a materially different "what to try next" strategy than autoresearch/evolution-kernel's single-lineage history read.

**Web research:** None — no citation sourcing, no literature loop. Entirely self-contained numeric optimization against your evaluator.

**Memory:** The population database itself *is* the memory (persisted programs + their scores across all islands) — much richer than a TSV or reflection-only log, at the cost of not being a real git-tracked repo state.

**Headless invocation (confirmed from README):**
```bash
python openevolve-run.py examples/function_minimization/initial_program.py \
  examples/function_minimization/evaluator.py \
  --config examples/function_minimization/config.yaml \
  --iterations 50
```
Also usable as a library: `from openevolve import evolve_function`. Docker image published too (`ghcr.io/algorithmicsuperintelligence/openevolve:latest`).

**Known weaknesses (from 89 open issues, sampled top 30):**
- Security: untrusted evaluator code runs in-process (no subprocess/sandbox isolation) and the visualizer has no auth (#481) — directly relevant to heartgold, which should sandbox its verify step.
- Novelty check ordering wastes compute (#439).
- Clobbered loggers when running multiple OpenEvolve instances in parallel (#295) — a concurrency bug that would bite anyone trying to fan out many repos at once.
- "Best program is the same as the initial one" reported with no clear diagnosis (#281) — i.e., sometimes the loop just doesn't find anything, with no visibility into why.
- No agentic/tree-search mode — issue #276 explicitly requests it, still open; openevolve is pure LLM-diff-mutation + evolutionary bookkeeping, not an agent that can explore a codebase with tools.
- No distributed evaluator (#355, open) — single-machine by default.
- "How to optimize the whole code repository?" (#413) is an **open question from a user**, not a supported workflow — confirms it's not designed for whole-repo agentic improvement out of the box (closer to function/kernel-level optimization, as seen in its own `examples/algotune/*` tasks).

---

## 4. avasis-ai/synth-loop — 1 star, 0 forks, 0 open issues (TypeScript)

**What it is:** A tiny, essentially-unused (1 star) side project built on the author's own `SynthCode` agent framework. Directly relevant because it's the only one of the five that explicitly "scrapes the web/other repos for patterns" as its improvement-sourcing mechanism — closest conceptual cousin to heartgold's "research the web for improvements."

**Loop steps ("Seven Phases"):** Discover (scrape one OSS repo per cycle from a hardcoded list of 15 — Claude Code, Aider, Cline, OpenHands, Codex, MCP SDK, Swarm, browser-use, e2b, Dify, Context7, Jina Reader, Firecrawl, Auto-GPT, computer-use — via GitHub API + optional Context7 docs, extract 5–20 design patterns) → Analyze (compare accumulated patterns against your codebase, rank gaps by impact) → Implement (write code + tests for top 3 gaps) → Secure (regex/pattern scan the git diff for API keys/secrets/`.env` before any push) → Verify (`tsc --noEmit`, `npm test`, `npm run build`; auto-spawns a fix agent on failure) → Publish (version bump, commit, push, optional `npm publish`) → **Self-Upgrade** (reinstalls its own just-published npm package and uses the new version for the next cycle).

**Verify/gate:** Binary — `tsc`/tests/build must all pass, and the secret scanner must find nothing, or the push is blocked and "the cycle rolls back." **No git worktree isolation** — it edits the actual working tree directly (confirmed: no "worktree" string anywhere in `src/`), relying on commit/push gating rather than sandboxed experimentation. No metric/scoring at all beyond pass/fail — there's no notion of "keep only if a number doesn't get worse," just "keep if it compiles, tests, and builds."

**Next-try selection:** Pure pattern-matching against a fixed curated list of 15 "world-class" repos cycled through in order; "top 3 gaps" picked by an LLM's own impact ranking — no formal scoring, no history-informed search.

**Web research:** Yes, but shallow — GitHub API scraping of a hardcoded repo list + optional Context7 docs API. No academic citations, no issue-tracker mining, no "papers."

**Memory across iterations:** `.synth-loop/state.json` (cycle count, consecutive failures, total improvements/failed, repos scanned, patterns discovered count, version, last commit) + `.synth-loop/history.jsonl` (append-only cycle results). Patterns "accumulate across cycles" but there's no indication of deduplication or ranking stability across restarts.

**Headless invocation (confirmed from README):**
```bash
npx @avasis-ai/synth-loop run ./my-project --auto-publish --self-upgrade
```
Requires a local Ollama instance (`qwen3-coder-next:79B` recommended) — i.e., designed for a beefy local GPU workstation, not a laptop.

**Known weaknesses:** Zero adoption (1 star/0 forks/0 issues — essentially a solo demo, no real-world battle testing); requires Ollama + a large local model (79B) to function at all, ruling out cheap/laptop use; curated 15-repo list is hardcoded and arbitrary, not query-driven, so it can't target "this repo's actual problems," only "patterns from famous agent repos"; auto-publishing to npm + self-reinstalling is a genuinely risky design (a bad self-upgrade could brick the next cycle) with no rollback path described beyond the verify/secret gates; no isolation of the working tree during edits.

---

## 5. gaasher/Agent-Loop-Skills — 179 stars, 19 forks, 1 open issue (Python, library of Claude-Skill-packaged loops)

**What it is:** A collection of ~25 generic "loop" Agent Skills (Markdown SKILL.md + optional stdlib-only tools/roles), each a template you bind to your own task. The directly relevant one is **`optimize-loop`** ("Code & optimization" category).

**`optimize-loop` steps (exact checklist from its SKILL.md):**
1. Setup: resolve `<mode>` (`code` refactor-under-test, or `sql` query-under-fixed-results), `<editable_files>`, `<gate_cmd>`, `<metric_cmd>`, `<sandbox_root>` (default `./sandbox`), `<budget>` (default 8), `<patience>` (default 3) — interactively via `AskUserQuestion` on Claude Code, or plain prompts elsewhere. Writes `loop.run.yaml`.
2. Iteration 0 baseline: run gate; if not green, **abort** (never starts optimizing from a broken state). Run metric, record as current best.
3. Snapshot every editable file to `<sandbox_root>/iter<N>/` (cheap file-copy sandboxing, not a git worktree or process sandbox).
4. Apply **one** focused change (concrete idea lists given per mode — guard-clause flattening, stdlib calls, dead-code removal for code; index additions, subquery→JOIN rewrites for SQL).
5. Check gate: code — `<gate_cmd>` exit code; sql — candidate `hash` must equal baseline `hash` (so SQL "correctness" means row-set match — note: does **not** catch changed row *order*, flagged explicitly as a known blind spot unless `ORDER BY` is manually eyeballed).
6. If gate fails → **discard**, restore the file snapshot, log reason, continue (gate failure is not even counted as a metric comparison).
7. If gate passes, compare metric: code mode uses a **lexicographic tuple** `(complexity, max_nesting, loc)` — a genuinely nice idea heartgold should steal: ties on the primary metric are broken by secondary/tertiary ones instead of a single scalar. SQL mode uses `median_ms` with a noise band (≥3% relative improvement required to count as a real gain — avoids keeping noise-level "wins").
8. Keep (strictly better) or discard (restore snapshot); append a TSV ledger row; stop at `<patience>` consecutive no-improvement iterations or `<budget>` hard cap; **always restore working files to the best iteration on exit**, even if the very last iteration was a discard.

**Verify/gate:** Binary pass/fail gate (tests, or hash match) that is explicitly called "non-negotiable" — "A green gate after a behaviour change means the gate is too weak, not that the change is safe; prefer holding behaviour identical over trusting a thin gate." Metric is a secondary, separate signal that must strictly improve (with a noise band for timing).

**Next-try selection:** A fixed menu of "change ideas" per mode that the agent works through — no history-driven or population-driven search; closer to a checklist than a search algorithm. Other loops in the same repo (`tournament-autoresearch`, `dueling-autoresearch`, `alpha-evolve`) add judge-based or population-based selection, but `optimize-loop` itself is simple hill-climbing.

**Web research:** Not in `optimize-loop` itself, but the repo ships a shared `literature-search` skill (Semantic Scholar + arXiv, optional OpenAlex/Perplexity Sonar/bgpt.pro, all stdlib-only, cached) that other loops (`ml-autoresearch`, `research-proposal`, `hypothesis-gen`) call for citation-backed ideas, and which **degrades gracefully to the caller's own WebSearch/WebFetch** if not installed. This pattern — a shared, swappable literature/web tool any loop can call, with automatic fallback — is one of the more mature pieces of design seen across all five repos, but it is *not wired into* the code-optimization loop; nobody in this ecosystem actually does "web research → cited code change → verify → keep" end to end.

**Memory across iterations:** TSV ledger per loop (`iter, complexity, max_nesting, loc, status, description`), file snapshots per iteration for instant revert. No cross-run memory; each invocation starts cold except for whatever `loop.run.yaml` config is reused.

**Headless invocation:** No explicit `claude -p` example in the docs (unlike autoresearch), but the standard pattern for Claude Code skills applies: `claude -p "Use the optimize-loop skill: refactor src/foo.py, keep tests green via 'pytest', minimize complexity, budget 8 iterations."` — invoked by natural-language description matching, not a slash command (skills auto-load by `description` match, no command namespace unless installed as a plugin).

**Known weaknesses:** Repo explicitly labeled "experimental — expect breaking changes" with only 1 open issue (low traffic, "Improve skills as loop" is the live one; project is young). Self-documented non-goals: "not fully-autonomous agents," "not domain-exhaustive." Multi-role loops (judge/tournament variants) only get real subagent isolation on Claude Code — everywhere else they run "inline" (serially, same context), which the authors admit undermines independence of judgment. `optimize-loop`'s own snapshot-based sandbox is just file copies in a subdirectory of the same repo — no process/network isolation at all (weaker than evolution-kernel's firejail, let alone a worktree).

---

## Cross-cutting takeaways

- **None of the five** combine all of: (a) isolated git worktree per candidate, (b) a hard mechanical test+metric gate, (c) algorithmic (not just LLM-vibes) selection of what to try next, (d) actual web/paper/competitor research with citations feeding the proposal, and (e) persistent cross-run memory beyond a flat log. Each repo nails 1–2 of these and is weak/absent on the rest.
- **Isolation maturity ranking:** evolution-kernel (worktree + firejail) > Agent-Loop-Skills optimize-loop (file snapshot only) > autoresearch (commit+revert in place, worktree only for the separate regression gate) > synth-loop (no isolation, works on live tree) > openevolve (no git concept at all — population DB, not a repo).
- **Verification rigor ranking:** Agent-Loop-Skills optimize-loop and autoresearch both treat the gate as hard/non-negotiable with explicit "a green gate doesn't mean safe" language; evolution-kernel's gate is LLM-judged by default (weaker, though they recommend anchoring it); openevolve's "gate" is just the evaluator score with cascading stages (cheap-first) but no separate correctness/regression check; synth-loop's gate is binary compile/test/build + secret-scan, no behavior-preservation concept.
- **Nobody does real citation-gated web research inside the optimize/verify/keep loop.** autoresearch's `/improve` and Agent-Loop-Skills' `literature-search` are the two pieces that come closest, and both are bolted on as separate, non-code-optimization-specific commands/skills, not integrated into a single headless "research → propose → isolate → verify → keep" pipeline. This is heartgold's clearest differentiator.
- **Headless/CI invocation is a first-class, documented pattern** for autoresearch (`claude -p "/autoresearch ..."` in GitHub Actions) and openevolve (`python openevolve-run.py ...`) and evolution-kernel (`evolution-kernel --config ... --loop`) and synth-loop (`npx ... run --auto-publish --self-upgrade`); Agent-Loop-Skills has no documented headless pattern at all, which is itself a gap heartgold can close by shipping exact `claude -p` recipes per loop.

---

## Benchmarks for agentic code improvement/optimization

| Benchmark | Scope | Environment | Mac-without-Docker feasibility |
|---|---|---|---|
| **GSO** (gso-bench/gso, NeurIPS'25, arXiv:2505.23671) | 102 real-world runtime-optimization tasks across 10 Python codebases; agent patch judged against expert developer's actual optimizing commit via a performance test | SWE-bench-style Docker harness per task (repo-specific deps) | Poor — needs per-task Docker images for reproducible envs; a handful of tasks *might* be hand-ported to a local venv but that defeats the "cheap, no setup" point |
| **SWE-Perf** (arXiv:2507.12415, SWE-Perf/swe-perf) | Repository-level performance-optimization tasks mined from real GitHub repos with before/after performance tests; explicitly built as a SWE-bench-style harness | SWE-bench Docker-based reproducible envs (confirmed in docs) | Poor — same Docker dependency as SWE-bench; a universal "singleton" Docker image exists in a related repo (gke-labs/sweperf) but it's still Docker |
| **KernelBench** (ScalingIntelligence/KernelBench, arXiv:2502.10517) | ~250 PyTorch-operator-to-GPU-kernel (CUDA) tasks, graded on correctness + speedup | Requires an actual NVIDIA GPU + CUDA toolchain; newer pipelines run candidate kernels on cloud GPUs via Modal | **Not feasible on Mac at all** — Apple Silicon has no CUDA; Docker doesn't solve this, you need rented NVIDIA GPU time regardless |
| **AlgoTune** (oripress/AlgoTune, NeurIPS 2025, algotune.io) | 154 widely-used pure-Python math/physics/CS functions (sorting, FFT, convolution, SVD, AES, gzip, etc.); goal is faster code with byte-identical/tolerance-matched output | **Pure pip install, no Docker, no GPU, CPU-only, stdlib+numpy/scipy** — already used as example tasks inside openevolve (`examples/algotune/*`) | **Best fit** — can cheaply run a 5–10 task subset directly on a Mac laptop in minutes; correctness check + wall-clock timing both run locally |
| **Agent-Loop-Skills `optimize-loop` examples** (not a published benchmark, but a usable micro-harness) | Its own `tools/metrics.py` (complexity/nesting/LOC) and `tools/bench.py` (SQLite query latency+hash) are tiny, stdlib-only, already-built dockerless harnesses | Local Python + SQLite | Trivially runs on a Mac; useful as a smoke-test harness while building heartgold, not as a "real" external benchmark to compare against |

**Recommendation:** Use **AlgoTune** (a 5–20 task subset) as the cheap, dockerless, Mac-native baseline for heartgold v0 benchmarking — it already has a correctness oracle + timing harness, zero GPU/Docker dependency, and is already the shared reference point openevolve uses, so results are directly comparable to a known competitor. Treat GSO/SWE-Perf as the "serious" benchmarks to target later once heartgold has access to Docker/cloud compute (both are the closest to "real repo, real regression" and are what reviewers/users will actually compare heartgold against). Skip KernelBench entirely unless/until heartgold targets GPU-kernel optimization specifically — it's hardware-gated, not setup-gated.
