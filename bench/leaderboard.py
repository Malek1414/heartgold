"""Write bench/LEADERBOARD.md: per (suite, tool), the latest VALID result of each fixture
(runs that hit the usage limit or read hidden files are excluded)."""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
best = {}  # (suite, label) -> {fixture: result}
for p in sorted((ROOT / "results").glob("*.json"), key=lambda p: json.loads(p.read_text()).get("when", "")):
    d = json.loads(p.read_text())
    key = (d.get("suite", "easy"), d.get("label") or d["tool"])
    for r in d["results"]:
        if r.get("invalid"):
            continue
        best.setdefault(key, {})[r["fixture"]] = r

out = ["# Leaderboard", "", "Same model (sonnet) and per-fixture budget for every tool; tools run in a sandbox that",
       "cannot read hidden tests. Hard suites: score = share of the gap from the naive code to the oracle closed.",
       "Speed suite: score = log10(speedup on a HIDDEN benchmark)/2 x (share of hidden results correct)^10;",
       "1.0 = 100x faster, 1.5 = 1000x. Timings re-measured one at a time on an idle machine.",
       "DQ = read hidden test data (scored 0). '-' = no valid run yet.", ""]
for suite in ("speed", "hard2", "hard", "easy"):
    rows = [(lab, rs) for (s, lab), rs in best.items() if s == suite]
    if not rows:
        continue
    fixtures = sorted({f for _, rs in rows for f in rs})
    def total(rs):
        return sum(0 if r.get("contaminated") else r["score"] for r in rs.values()) / len(fixtures)
    rows.sort(key=lambda x: -total(x[1]))
    out += [f"## {suite} suite", "", "| tool | score | " + " | ".join(fixtures) + " | cost | time |",
            "|---|---|" + "---|" * len(fixtures) + "---|---|"]
    for lab, rs in rows:
        cells = ["DQ" if f in rs and rs[f].get("contaminated") else (f"{rs[f]['score']:.3f}" if f in rs else "-") for f in fixtures]
        cost = sum(r["cost_usd"] for r in rs.values())
        secs = sum(r["seconds"] for r in rs.values())
        out.append(f"| {lab} | **{total(rs):.3f}** | " + " | ".join(cells) + f" | ${cost:.2f} | {secs // 60}m |")
    out.append("")
(ROOT / "LEADERBOARD.md").write_text("\n".join(out) + "\n")
print("\n".join(out))
