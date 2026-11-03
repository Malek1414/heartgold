"""Re-score finished runs against the current hidden tests (after an oracle fix) without re-running tools."""
import json, pathlib, shutil, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import run as R

for path in sys.argv[1:]:
    d = json.loads(pathlib.Path(path).read_text())
    for r in d["results"]:
        work, fx = pathlib.Path(r["work"]), R.FIX / r["fixture"]
        if not work.exists():
            continue
        shutil.rmtree(work / "_hidden_tests", ignore_errors=True)
        shutil.copytree(fx / "hidden", work / "_hidden_tests")
        shutil.copy(next((fx / "hidden").glob("test_*.py")), work / "tests" / "_hidden_check.py")
        hp, ht = R.pytest_counts(work, "tests/_hidden_check.py")
        meta = json.loads((fx / "meta.json").read_text())
        noop = meta.get("noop_pass")
        hidden = max(0.0, (hp - noop) / (ht - noop)) if noop is not None and ht > noop else (hp / ht if ht else 0)
        clean = 1.0 if r["visible"].split("/")[0] == r["visible"].split("/")[1] else 0.0
        r.update(hidden=round(hidden, 3), hidden_raw=f"{hp}/{ht}",
                 score=round(0.7 * hidden + 0.2 * r["speed"] + 0.1 * clean if r["speed"] is not None else 0.9 * hidden + 0.1 * clean, 3))
    d["score"] = round(sum(r["score"] for r in d["results"]) / len(d["results"]), 3)
    pathlib.Path(path).write_text(json.dumps(d, indent=2))
    print(path, d["score"], [(r["fixture"], r["hidden_raw"]) for r in d["results"]])
