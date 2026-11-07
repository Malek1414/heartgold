"""Metric mode's keep/drop logic, end to end on a tiny repo, with a scripted agent instead of claude."""
import json, pathlib, subprocess, sys, textwrap

import heartgold.metric as M

EVAL = textwrap.dedent('''
    import json, os, sys
    from model import predict
    tune = [(x, x % 3 == 0) for x in range(30)]
    test = [(x, x % 3 == 0) for x in range(30, 60)]
    data = test if "--test" in sys.argv else tune
    if "--test" in sys.argv and os.environ.get("HEARTGOLD_HOLDOUT") != "1":
        sys.exit("held out")
    hits = [float(predict(x) == y) for x, y in data]
    print(json.dumps({"acc": sum(hits) / len(hits), "per_question": {"acc": hits}}))
''')
MODEL = "def predict(x):\n    return False\n"
TEST = "from model import predict\n\ndef test_returns_bool():\n    assert predict(3) in (True, False)\n"

# What the scripted agent writes for each idea.
CHANGES = {
    "generalises": "def predict(x):\n    return x % 3 == 0\n",
    "memorises tune data": "def predict(x):\n    return x < 30 and x % 3 == 0 or x >= 30\n",
    "breaks tests": "def predict(x):\n    return 'maybe'\n",
}


def fake_claude(prompt, cwd, *a, **kw):
    if "list the 6 most promising" in prompt:
        return json.dumps({"ideas": [{"name": n, "how": n} for n in CHANGES]})
    for name, code in CHANGES.items():
        if f"implement now: {name}" in prompt:
            (pathlib.Path(cwd) / "model.py").write_text(code)
    return "done"


def test_keeps_what_generalises_and_drops_overfitting(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "eval.py").write_text(EVAL)
    (repo / "model.py").write_text(MODEL)
    (repo / "tests").mkdir()
    (repo / "tests" / "test_model.py").write_text(TEST)
    subprocess.run("git init -q && git add -A && git -c user.email=a@a -c user.name=a commit -qm init", cwd=repo, shell=True, check=True)
    monkeypatch.setattr(M, "claude", fake_claude)
    run = M.MetricRun(str(repo), "raise acc", f"{sys.executable} eval.py", f"{sys.executable} eval.py --test",
                      metric="acc", protect=["eval.py"], rounds=1, candidates=3, budget=100,
                      test_cmd=f"{sys.executable} -m pytest -q -p no:cacheprovider")
    assert run.run() is True
    ledger = [json.loads(l) for l in (repo / ".heartgold" / "ledger.jsonl").read_text().splitlines()]
    done = next(e for e in ledger if e["event"] == "metric.done")
    assert done["kept"] == ["generalises"]
    assert "acc 1.000" in done["holdout"]
    assert (repo / "model.py").read_text() == CHANGES["generalises"]
    attempts = {e["idea"]: e for e in ledger if e["event"] == "metric.attempt"}
    assert attempts["breaks tests"]["tests"] is False
    # the agents' command could not read held-out numbers
    assert subprocess.run([sys.executable, "eval.py", "--test"], cwd=repo, capture_output=True).returncode != 0


def test_drops_a_tune_gain_that_hurts_held_out(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "eval.py").write_text(EVAL)
    (repo / "model.py").write_text(MODEL)
    subprocess.run("git init -q && git add -A && git -c user.email=a@a -c user.name=a commit -qm init", cwd=repo, shell=True, check=True)
    only = {"memorises tune data": CHANGES["memorises tune data"]}
    monkeypatch.setattr(M, "claude", lambda p, cwd, *a, **k: json.dumps({"ideas": [{"name": "memorises tune data", "how": ""}]}) if "list the 6" in p
                        else ((pathlib.Path(cwd) / "model.py").write_text(only["memorises tune data"]) or "done"))
    run = M.MetricRun(str(repo), "raise acc", f"{sys.executable} eval.py", f"{sys.executable} eval.py --test",
                      metric="acc", protect=["eval.py"], rounds=1, candidates=1, budget=100, test_cmd="true")
    assert run.run() is False
    assert (repo / "model.py").read_text() == MODEL
    ledger = [json.loads(l) for l in (repo / ".heartgold" / "ledger.jsonl").read_text().splitlines()]
    assert any(e["event"] == "metric.holdout_gate" and e["kept"] is False for e in ledger)
