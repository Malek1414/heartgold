"""Headless coding-agent calls (claude -p) with cost tracking."""
import json, os, subprocess, sys

COST = {"usd": 0.0}


class BudgetExceeded(Exception):
    pass


def claude(prompt, cwd, model="sonnet", budget=1.0, timeout=900, tools=None):
    """Run one headless agent turn in `cwd`. Returns the final text."""
    cmd = ["claude", "-p", "--model", model, "--dangerously-skip-permissions",
           "--setting-sources", "project", "--strict-mcp-config", "--no-session-persistence",
           "--output-format", "json", "--max-budget-usd", f"{budget:.2f}"]
    if tools:
        # one token: as a separate argument the variadic flag would swallow the prompt that follows
        cmd += [f"--allowedTools={','.join(tools)}"]
    try:
        # stdin closed: `claude -p` appends piped stdin to the prompt, which must never happen here
        p = subprocess.run(cmd + [prompt], cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL)
        out = p.stdout
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return out
    COST["usd"] += data.get("total_cost_usd", 0.0) or 0.0
    if data.get("subtype") not in (None, "success") or data.get("is_error"):
        print(f"HEARTGOLD_AGENT_STOP subtype={data.get('subtype')} turns={data.get('num_turns')} "
              f"cost={data.get('total_cost_usd')}", flush=True)
    if data.get("api_error_status") == 429 or "hit your session limit" in (data.get("result") or ""):
        # usage limit: any result from here on would be garbage, so stop the whole run at once
        print(f"HEARTGOLD_RATE_LIMITED {data.get('result', '')}\nHEARTGOLD_COST_USD={COST['usd']:.4f}", flush=True)
        sys.stdout.flush()
        os._exit(3)
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
