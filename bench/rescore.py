# Copyright 2026 Malek Hassan (https://github.com/Malek1414/heartgold)
# SPDX-License-Identifier: Apache-2.0
"""Re-score finished runs against the current hidden tests (after an oracle fix) without re-running tools."""
import json, pathlib, shutil, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import run as R

import math


def quiet_speed(r, work, fx, meta):
    """Re-time the hidden benchmark with nothing else running (5 runs, best)."""
    shutil.copy(fx / "hidden" / "bench_hidden.py", work / "_bench_hidden.py")
    best = None
    for _ in range(5):
        code, out, _ = R.sh(f"{R.PY} _bench_hidden.py", work, 300)
        try:
            v = float(out.strip().splitlines()[-1]) if code == 0 else None
        except (ValueError, IndexError):
            v = None
        if v is None:
            return
        best = v if best is None else min(best, v)
    hp, ht = map(int, r["hidden_raw"].split("/"))
    frac = hp / ht if ht else 0.0
    speedup = meta["base_hidden_time"] / best
    speed = math.log10(speedup) / 2 if speedup > 1 else 0.0
    r.update(after_time=best, speedup=round(speedup, 1), speed=round(speed, 3), score=round(frac ** 10 * speed, 3), quiet=True)


for path in sys.argv[1:]:
    d = json.loads(pathlib.Path(path).read_text())
    for r in d["results"]:
        work, fx = pathlib.Path(r["work"]), R.FIX / r["fixture"]
        if not work.exists():
            continue
        meta = json.loads((fx / "meta.json").read_text())
        if meta.get("speed_mode") == "open":
            if not r.get("invalid"):
                quiet_speed(r, work, fx, meta)
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
    v = [r for r in d["results"] if not r.get("invalid")]
    d["score"] = round(sum(r["score"] for r in v) / len(v), 3) if v else 0.0
    pathlib.Path(path).write_text(json.dumps(d, indent=2))
    print(path, d["score"], [(r["fixture"], r["hidden_raw"]) for r in d["results"]])
