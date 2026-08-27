#!/usr/bin/env python3
"""Bench-dsv4 grader. Master run: python3 grader.py <run_dir> [hidden_instances_dir]
Agent self-run:   python3 task/grader/grader.py .
Checksum enforcement only when manifest.json sits next to THIS script file.
"""
import json, hashlib, os, re, subprocess, sys, time

BUDGET_FAST, TIMEOUT = 60, 120
ANTI_CHEAT = ["import requests", "import urllib", "import socket", "import http",
              "urlopen", "expected.json", "subprocess", "import minisat",
              "pycosat", "pysat"]
# Hidden-instance names must never appear in solver.py — the only way to use
# them is special-casing, which the exercise forbids.
ANTI_CHEAT_HIDDEN_NAMES = ["php9", "rand220", "coloring14"]

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

def verify_manifest(run_dir, script_dir):
    mpath = os.path.join(script_dir, "manifest.json")
    if not os.path.exists(mpath):
        return {"ok": True, "note": "no manifest (self-run)"}
    man = json.load(open(mpath))
    bad = []
    for rel, want in man.items():
        p = os.path.join(run_dir, "task", rel)
        if not os.path.exists(p) or sha(p) != want:
            bad.append(rel)
    # no extra files inside task/ (agents must not add anything)
    base = os.path.join(run_dir, "task")
    for root, _, files in os.walk(base):
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), base)
            if rel not in man and not rel.startswith("grader/scorecard"):
                bad.append("EXTRA:" + rel)
    return {"ok": not bad, "tampered": bad}

def parse_cnf(path):
    nvars, clauses = None, []
    cur = []
    for line in open(path):
        line = line.split("%")[0].strip()
        if not line or line.startswith("c"):
            continue
        toks = line.split()
        if toks[0] == "p":
            assert toks[1] == "cnf"
            nvars, ncl = int(toks[2]), int(toks[3])
        else:
            for t in toks:
                lit = int(t)
                if lit == 0:
                    if cur:
                        clauses.append(cur)
                    cur = []
                else:
                    cur.append(lit)
    if cur:
        clauses.append(cur)
    return nvars, clauses

def parse_answer(out):
    toks = out.split()
    if not toks:
        return None, None
    if toks[0].upper() == "UNSAT":
        return "UNSAT", None
    if toks[0].upper() != "SAT":
        return None, None
    try:
        lits = [int(t) for t in toks[1:]]
    except ValueError:
        return None, None
    return "SAT", lits

def verify_model(nvars, clauses, lits):
    if lits is None:
        return "no model for SAT"
    asn = {}
    for l in lits:
        v = abs(l)
        if v == 0 or v > nvars or v in asn:
            return "bad literal or duplicate var"
        asn[v] = l > 0
    if len(asn) != nvars:
        return f"model covers {len(asn)}/{nvars} vars"
    for cl in clauses:
        if not any((l > 0) == asn[abs(l)] for l in cl):
            return "unsatisfied clause"
    return None

def run_instance(py, solver, cnf, cwd):
    t0 = time.time()
    try:
        r = subprocess.run([py, solver, cnf], capture_output=True, text=True,
                           timeout=TIMEOUT, cwd=cwd)
        dt = time.time() - t0
        out = (r.stdout or "") + "\n" + (r.stderr or "")
        verdict, model = parse_answer(out)
        return {"wall": dt, "verdict": verdict, "model": model,
                "exit": r.returncode, "raw": out[:400]}
    except subprocess.TimeoutExpired:
        return {"wall": TIMEOUT, "verdict": "TIMEOUT", "model": None,
                "exit": -1, "raw": ""}

def main():
    run_dir = os.path.abspath(sys.argv[1])
    hidden_dir = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
    script_dir = os.path.dirname(os.path.abspath(__file__))
    py = sys.executable
    inst = os.path.join(run_dir, "task", "grader", "instances")
    expected = json.load(open(os.path.join(inst, "expected.json")))

    report = {"manifest": verify_manifest(run_dir, script_dir), "instances": {}}

    solver = os.path.join(run_dir, "solver.py")
    if not os.path.exists(solver):
        report["fatal"] = "solver.py missing"
        json.dump(report, open(os.path.join(run_dir, "scorecard.json"), "w"), indent=1)
        print(json.dumps(report, indent=1))
        return

    groups = {"visible": [], "hidden": []}
    for d, key in [(inst, "visible"), (hidden_dir, "hidden")]:
        if d and os.path.isdir(d):
            groups[key] = sorted(f for f in os.listdir(d) if f.endswith(".cnf"))

    results = {}
    dirs = {"visible": inst, "hidden": hidden_dir or ""}
    for key, files in groups.items():
        d = dirs[key]
        for fn in files:
            name = fn[:-4]
            exp = expected.get(name, {}).get("verdict")
            cnf_path = os.path.join(d, fn)
            r = run_instance(py, solver, cnf_path, run_dir)
            nvars, clauses = parse_cnf(cnf_path)
            if r["verdict"] == "SAT":
                err = verify_model(nvars, clauses, r["model"])
                r["model_ok"] = err is None
                r["model_err"] = err
            elif r["verdict"] == "UNSAT":
                r["model_ok"], r["model_err"] = True, None
            else:
                r["model_ok"], r["model_err"] = False, "no verdict"
            ok = r["model_ok"] and r["verdict"] == exp
            r["correct"] = bool(ok)
            results[name] = r
    report["instances"] = results

    # anti-cheat scan
    flags = []
    for f in ["solver.py", "encode_coloring.py"]:
        p = os.path.join(run_dir, f)
        if os.path.exists(p):
            src = open(p).read()
            for pat in ANTI_CHEAT:
                if pat in src:
                    flags.append(f"{f}: {pat}")
            for name in ANTI_CHEAT_HIDDEN_NAMES:
                if name in src:
                    flags.append(f"{f}: hidden-instance name '{name}' (special-casing)")
    report["anti_cheat"] = flags

    # scoring
    vis_n = len(groups["visible"])
    hid_n = len(groups["hidden"])
    def score(name, pool, count):
        r = results.get(name)
        if not r or not r["correct"]:
            return 0.0
        share = pool / count
        if r["wall"] <= BUDGET_FAST:
            return share
        return share / 2

    pa_vis = sum(score(n, 60, vis_n) for n in (f[:-4] for f in groups["visible"])) if vis_n else 0
    pa_hid = sum(score(n, 10, hid_n) for n in (f[:-4] for f in groups["hidden"])) if hid_n else 0

    # Part B: coloring
    pb = {"score": 0, "details": []}
    enc = os.path.join(run_dir, "encode_coloring.py")
    cjson = os.path.join(inst, "coloring12.json")
    sol = os.path.join(run_dir, "coloring_solution.json")
    if os.path.exists(enc):
        pb["details"].append("encoder exists")
        r = subprocess.run([py, enc], capture_output=True, text=True, timeout=60,
                           cwd=run_dir)
        cnf = os.path.join(run_dir, "coloring.cnf")
        if r.returncode == 0 and os.path.exists(cnf):
            pb["score"] += 5
            pb["details"].append("coloring.cnf produced")
            nvars, clauses = parse_cnf(cnf)
            spec = json.load(open(cjson))
            want = spec["n"] * spec["k"]
            if nvars == want and len(clauses) == spec["n"] + spec["n"] * spec["k"] * (spec["k"] - 1) // 2 + len(spec["edges"]) * spec["k"]:
                pb["score"] += 5
                pb["details"].append("cnf shape correct")
                r2 = run_instance(py, solver, cnf, run_dir)
                if r2["verdict"] == "SAT":
                    err = verify_model(nvars, clauses, r2["model"])
                    if err is None:
                        colors = []
                        asn = {abs(l): l > 0 for l in r2["model"]}
                        for v in range(spec["n"]):
                            for c in range(spec["k"]):
                                if asn.get(v * spec["k"] + c + 1, False):
                                    colors.append(c)
                                    break
                        if len(colors) == spec["n"] and \
                           all(0 <= c < spec["k"] for c in colors) and \
                           all(colors[u] != colors[v] for u, v in spec["edges"]):
                            pb["score"] += 10
                            pb["details"].append("coloring valid")
                            if os.path.exists(sol):
                                try:
                                    s = json.load(open(sol))
                                    if s.get("colors") == colors:
                                        pb["details"].append("solution json matches")
                                except Exception:
                                    pb["details"].append("solution json unreadable")
                        else:
                            pb["details"].append("coloring INVALID")
                    else:
                        pb["details"].append("cnf model invalid: " + err)
                else:
                    pb["details"].append("solver failed on coloring.cnf")
            else:
                pb["details"].append("cnf shape wrong")
        else:
            pb["details"].append("encoder failed to run")
    else:
        pb["details"].append("encode_coloring.py missing")
    report["partB"] = pb

    notes = os.path.join(run_dir, "notes.md")
    if os.path.exists(notes):
        txt = open(notes).read()
        report["notes"] = {"exists": True, "words": len(txt.split()),
                           "has_timing": bool(re.search(r"\d+(\.\d+)?\s*s", txt))}
    else:
        report["notes"] = {"exists": False}

    report["scores"] = {"partA_visible": round(pa_vis, 1), "partA_hidden": round(pa_hid, 1),
                        "partB": pb["score"], "notes_cap": 10 if report["notes"]["exists"] else 0}
    json.dump(report, open(os.path.join(run_dir, "scorecard.json"), "w"), indent=1)
    print(json.dumps(report, indent=1))

if __name__ == "__main__":
    main()
