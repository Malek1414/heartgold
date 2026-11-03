"""Web research: queries -> passages -> cited requirements, with a verbatim-quote gate."""
import json, re, shutil, subprocess
from concurrent.futures import ThreadPoolExecutor

from .agent import claude, extract_json


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def search_passages(query, n=4, k=6):
    if not shutil.which("searchify"):
        return []
    try:
        p = subprocess.run(["searchify", "passages", query, "-n", str(n), "-k", str(k), "--max-chars", "900"],
                           capture_output=True, text=True, timeout=240)
        out = p.stdout
        data = json.loads(out[out.index("{"):])
        return [dict(query=query, url=r["url"], title=r.get("title", ""), text=r.get("content", ""))
                for r in data.get("results", []) if r.get("content")]
    except Exception:
        return []


def research(goal, code_summary, workdir, model, budget, log):
    q_reply = claude(
        "You plan web research for a code change. Goal:\n" + goal +
        "\n\nCode:\n" + code_summary +
        "\n\nWrite 4 web search queries that find the AUTHORITATIVE source (spec, RFC, official docs, "
        "the canonical algorithm description) plus known edge cases / pitfalls / bug reports for this goal. "
        'Reply only with JSON: {"queries": ["...", ...]}',
        workdir, model, budget * 0.1, tools=[])
    queries = (extract_json(q_reply, {}) or {}).get("queries", [])[:5] or [goal[:200]]
    log("research.queries", queries=queries)
    with ThreadPoolExecutor(4) as ex:
        passages = [p for ps in ex.map(search_passages, queries) for p in ps]
    seen, uniq = set(), []
    for p in passages:
        key = _norm(p["text"])[:200]
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    passages = uniq[:24]
    log("research.passages", n=len(passages), urls=sorted({p["url"] for p in passages}))
    src = "\n\n".join(f"[{i}] {p['url']}\n{p['text']}" for i, p in enumerate(passages))
    r_reply = claude(
        "Goal:\n" + goal + "\n\nCode:\n" + code_summary + "\n\nResearch passages:\n" + (src or "(none found)") +
        "\n\nList every concrete, testable requirement the finished code must meet to fully satisfy the goal, "
        "INCLUDING subtle edge cases the current code gets wrong and edge cases the goal implies but does not "
        "spell out (empty input, boundaries, invalid input handling, ordering, unicode, large input, performance). "
        "For each requirement give: an example input and the exact expected output/behaviour; and, if a passage "
        "supports it, the passage index and a short VERBATIM quote copied from that passage. "
        "Do not invent requirements that contradict the goal text or the existing tests. "
        'Reply only with JSON: {"requirements": [{"id": "R1", "text": "...", "example": "...", '
        '"source": 3, "quote": "..."}]} (source/quote null if unsourced).',
        workdir, model, budget * 0.25, tools=[])
    reqs = (extract_json(r_reply, {}) or {}).get("requirements", [])
    for r in reqs:
        idx, quote = r.get("source"), r.get("quote")
        ok = (isinstance(idx, int) and 0 <= idx < len(passages) and quote
              and _norm(quote) and _norm(quote) in _norm(passages[idx]["text"]))
        r["verified"] = bool(ok)
        r["url"] = passages[idx]["url"] if ok else None
        if not ok:
            r["quote"] = None
    log("research.requirements", n=len(reqs), verified=sum(r["verified"] for r in reqs))
    return reqs, passages
