---
name: heartgold
description: >
  Research-driven code improver that proves its changes before keeping them. Use this skill when the user
  wants to make code faster without changing its results ("make this faster", "optimize X", "speed up Y",
  "reduce latency/allocations in Z"), or wants an implementation built strictly to a written specification
  with evidence it is correct ("implement X to spec", "build a compliant Y", "match the RFC/spec for Z",
  "with proof it's right"). It points the heartgold CLI at a target git repo and a goal, lets it research how
  the best people solve the problem, try several implementations in isolated git worktrees, and merge only the
  attempts that pass an identical-output oracle (speed goals) or spec-cited tests (correctness goals). Do not
  use it for trivial one-line edits, for repos without tests, or when the user wants a change applied without
  verification.
---

# heartgold

heartgold is a Python CLI that improves a target repo against a goal and only keeps changes it can prove are
better. It never edits the target repo's Python logic directly — it drives the `heartgold` package, which does
the research/implement/verify/merge loop in git worktrees.

## 1. Check requirements before running

heartgold needs, on the machine running it:

- Python 3.11+ (stdlib only for heartgold itself — no pip install needed for the tool).
- The target repo's own test setup: `pytest` (and `pytest-timeout`) available in the environment that runs
  the target repo's tests.
- The `claude` CLI on `PATH` (`claude -p ...`) — heartgold shells out to it as the coding agent for every
  candidate implementation.
- Optional but recommended: `gh` (authenticated) for GitHub code search, and a `searchify` CLI for web
  research. heartgold degrades gracefully (skips that research source) if either is missing — check with
  `which gh` / `which searchify` and mention to the user if absent, but don't block the run on it.

If the user's environment doesn't have `claude`/`gh`/`searchify` set up, tell them what's missing rather than
silently running a degraded loop, unless they've already acknowledged it.

## 2. Install / locate heartgold itself

This skill ships inside the `heartgold` plugin. The plugin root is `${CLAUDE_PLUGIN_ROOT}` and the Python
package lives at `${CLAUDE_PLUGIN_ROOT}/heartgold`. heartgold has no third-party Python dependencies (only
stdlib), so there is nothing to `pip install` for heartgold itself — just make sure `python3` resolves to
3.11+:

```bash
python3 --version
```

If the user wants it as an isolated environment anyway (e.g. to pin `pytest`/`pytest-timeout` for the target
repo), prefer `uv`:

```bash
uv venv "${CLAUDE_PLUGIN_ROOT}/.venv"
uv pip install --python "${CLAUDE_PLUGIN_ROOT}/.venv/bin/python" pytest pytest-timeout
```

falling back to plain pip if `uv` is not installed:

```bash
python3 -m venv "${CLAUDE_PLUGIN_ROOT}/.venv"
"${CLAUDE_PLUGIN_ROOT}/.venv/bin/pip" install pytest pytest-timeout
```

## 3. Run it

Run as a module from the plugin directory (`PYTHONPATH` set to the plugin root so `heartgold` resolves),
pointed at the user's target repo:

```bash
cd "${CLAUDE_PLUGIN_ROOT}" && python3 -m heartgold run /absolute/path/to/target/repo --goal "Make lcs_length as fast as possible without changing its results"
```

Key flags (all optional besides repo + goal):

```
python -m heartgold run REPO --goal "..." | --goal-file goal.md
    --budget-usd 3.0       total agent spend for the run (default 3.0)
    --time-limit 1500      wall-clock seconds for the whole run (default 1500)
    --model sonnet         model used for the headless `claude -p` agent calls
    --candidates 3         candidate implementations per round
    --diff-rounds 2
    --test-cmd / --bench-cmd   override auto-detected test/bench commands
```

heartgold picks its mode from the goal text:
- **Speed mode**: triggers when the goal contains speed language (e.g. "as fast as possible", "only goal...
  speed") AND the target repo has a `bench.py`. It builds an identical-output oracle, independent benchmarks,
  and adversarial worst-case benchmarks before trusting any "faster" claim.
- **Spec mode**: everything else. It researches the actual specification with verbatim-quote citations, writes
  tests from it, builds candidates, and resolves disagreements with a spec-reading judge.

Before running, confirm with the user: the exact goal text, the target repo path, and roughly how much budget
(`--budget-usd`) and time (`--time-limit`) they're comfortable with — heartgold spends real `claude -p` budget
per run.

## 4. Read the results afterward

Everything heartgold does is logged inside the **target repo**, not the plugin:

- `.heartgold/report.md` — human-readable summary: what was tried, what was kept, and why. Read this first and
  summarize it for the user.
- `.heartgold/ledger.jsonl` — append-only JSON-lines log of every attempt, research source, and score. Useful
  for digging into *why* a specific candidate was rejected, or what sources backed a kept change.
- `.heartgold/map.json` — the detected language/test/bench commands for the repo.

To summarize a run:

```bash
cat /absolute/path/to/target/repo/.heartgold/report.md
```

For a specific failed/kept attempt, grep the ledger:

```bash
grep -i "<candidate or proposal name>" /absolute/path/to/target/repo/.heartgold/ledger.jsonl
```

Report back to the user: whether anything was kept, the measured improvement (speedup, or which spec
requirements are now covered by tests), and point them at `.heartgold/report.md` and the git diff/commits
heartgold produced in their repo. Never claim a result heartgold itself didn't verify — the whole point of the
tool is that unverified "it should be faster" claims are discarded.
