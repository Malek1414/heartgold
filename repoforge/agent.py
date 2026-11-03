"""Headless coding-agent calls (claude -p) with cost tracking."""
import json, subprocess

COST = {"usd": 0.0}


class BudgetExceeded(Exception):
    pass


def claude(prompt, cwd, model="sonnet", budget=1.0, timeout=900, tools=None):
    """Run one headless agent turn in `cwd`. Returns the final text."""
    cmd = ["claude", "-p", "--model", model, "--dangerously-skip-permissions",
           "--setting-sources", "project", "--strict-mcp-config", "--no-session-persistence",
           "--output-format", "json", "--max-budget-usd", f"{budget:.2f}"]
    if tools:
        cmd += ["--allowedTools", ",".join(tools)]
    try:
        p = subprocess.run(cmd + [prompt], cwd=cwd, capture_output=True, text=True, timeout=timeout)
        out = p.stdout
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return out
    COST["usd"] += data.get("total_cost_usd", 0.0) or 0.0
    return data.get("result", "") or ""


def extract_json(text, default=None):
    """Pull the last JSON object/array out of an agent reply."""
    for opener, closer in (("```json", "```"),):
        if opener in text:
            chunk = text.rsplit(opener, 1)[1].split(closer, 1)[0]
            try:
                return json.loads(chunk)
            except json.JSONDecodeError:
                pass
    for start_ch in "{[":
        idx = text.find(start_ch)
        while idx != -1:
            try:
                return json.JSONDecoder().raw_decode(text[idx:])[0]
            except json.JSONDecodeError:
                idx = text.find(start_ch, idx + 1)
    return default
