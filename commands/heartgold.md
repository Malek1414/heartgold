---
name: heartgold
description: "Run heartgold against a repo with a goal: research, implement candidates in isolated worktrees, verify, keep only what's proven better"
argument-hint: "[path/to/repo] --goal \"...\" [--budget-usd N] [--time-limit SECS] [--model sonnet]"
---

Run the heartgold CLI using `$ARGUMENTS` as the arguments to `python -m heartgold run`.

Follow the `heartgold` skill for full details (requirements, install, how to read results). In short:

1. Parse `$ARGUMENTS` for the target repo path and `--goal`/`--goal-file` text. If no goal is given, ask the
   user for the goal before running anything.
2. Confirm `claude` is on `PATH` (heartgold shells out to it), and check for optional `gh` / `searchify`.
3. Run from the plugin root so the `heartgold` package resolves:

```bash
cd "${CLAUDE_PLUGIN_ROOT}" && python3 -m heartgold run $ARGUMENTS
```

4. When it finishes, read and summarize `.heartgold/report.md` from the target repo (and `.heartgold/ledger.jsonl`
   if the user wants attempt-by-attempt detail). Report only what heartgold itself verified — kept changes,
   measured speedup, or which spec requirements now have passing cited tests.
