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


def extract_page(url):
    try:
        p = subprocess.run(["searchify", "extract", url], capture_output=True, text=True, timeout=180)
        data = json.loads(p.stdout[p.stdout.index("{"):])
        r = (data.get("results") or [{}])[0]
        return r.get("content") or ""
    except Exception:
        return ""


def fetch_specs(goal, passages, workdir, model, budget, log, spec_dir):
    """Find the canonical specification document(s) and save their FULL text for the agents."""
    urls = "\n".join(sorted({p["url"] for p in passages}))
    reply = claude(
        "Goal:\n" + goal + "\n\nURLs seen during research:\n" + (urls or "(none)") +
        "\n\nName up to 3 URLs of the AUTHORITATIVE primary documents that define the required behaviour "
        "(the RFC / PEP / man page / official spec / reference implementation docs), preferring plain-text or "
        "HTML versions (e.g. rfc-editor.org/rfc/rfcNNNN.txt, peps.python.org, man7.org, git-scm.com/docs). "
        "You may use URLs not in the list if you are sure they exist. "
        'Reply only with JSON: {"urls": ["..."]}',
        workdir, model, budget, tools=[])
    want = ((extract_json(reply, {}) or {}).get("urls") or [])[:3]
    spec_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    with ThreadPoolExecutor(3) as ex:
        for url, text in zip(want, ex.map(extract_page, want)):
            if len(text) > 800:
                name = re.sub(r"[^a-zA-Z0-9]+", "_", url.split("//", 1)[-1])[:80] + ".md"
                (spec_dir / name).write_text(f"Source: {url}\n\n{text[:150000]}")
                saved.append(url)
    log("research.specs", wanted=want, saved=saved)
    return saved
