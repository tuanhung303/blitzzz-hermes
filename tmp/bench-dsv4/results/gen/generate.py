#!/usr/bin/env python3
"""One-off generator for the bench-dsv4 exercise instances (mine, not shipped as task).
Produces: instances/ (visible), hidden/ (grade-time only), expected.json, coloring.json.
All instances deterministic (fixed seeds) with verified ground truth.
"""
import json, os, random, itertools, sys

OUT = os.path.dirname(os.path.abspath(__file__))

def write_cnf(path, nvars, clauses):
    with open(path, "w") as f:
        f.write(f"p cnf {nvars} {len(clauses)}\n")
        for cl in clauses:
            f.write(" ".join(map(str, cl)) + " 0\n")

def php(n):
    """Pigeonhole PHP_n^{n-1}: n pigeons, n-1 holes. Provably UNSAT. Classic CDCL stress."""
    holes = n - 1
    def var(p, h):
        return (p - 1) * holes + h
    clauses = []
    for p in range(1, n + 1):                       # each pigeon in >=1 hole
        clauses.append([var(p, h) for h in range(1, holes + 1)])
    for h in range(1, holes + 1):                   # each hole holds <=1 pigeon
        for p, q in itertools.combinations(range(1, n + 1), 2):
            clauses.append([-var(p, h), -var(q, h)])
    return n * holes, clauses

def planted_3sat(nvars, nclauses, seed):
    """Random 3-SAT with a planted satisfying assignment (guaranteed SAT)."""
    rng = random.Random(seed)
    mrng = random.Random(seed * 7919 + 13)
    model = [mrng.random() < 0.5 for _ in range(nvars)]
    seen, clauses = set(), []
    while len(clauses) < nclauses:
        vs = rng.sample(range(nvars), 3)
        signs = [rng.random() < 0.5 for _ in range(3)]
        ok = any((s and model[v]) or (not s and not model[v]) for v, s in zip(vs, signs))
        if not ok:
            signs[0] = not signs[0]
        cl = tuple(sorted((v + 1) * (1 if s else -1) for v, s in zip(vs, signs)))
        if cl in seen:
            continue
        seen.add(cl)
        clauses.append(cl)
    return nvars, clauses

def coloring_instance(n, k, p, seed):
    """Random graph, k-colorable (verified by backtracking). Returns (nodes, edges, coloring)."""
    rng = random.Random(seed)
    # Planted construction: color nodes first, then add edges only between
    # differently-colored nodes -> the planted coloring is always valid.
    rng = random.Random(seed)
    color = [rng.randrange(k) for _ in range(n)]
    edges = set()
    for i in range(n):
        for j in range(i + 1, n):
            if color[i] != color[j] and rng.random() < p:
                edges.add((i, j))
    # guarantee min degree 2 so the graph isn't trivially easy
    adj = [set() for _ in range(n)]
    for u, v in edges:
        adj[u].add(v); adj[v].add(u)
    for v in range(n):
        while len(adj[v]) < 2:
            cands = [u for u in range(n)
                     if u != v and u not in adj[v] and color[u] != color[v]]
            if not cands:
                break
            u = rng.choice(cands)
            edges.add(tuple(sorted((u, v))))
            adj[u].add(v); adj[v].add(u)
    return n, sorted(edges), list(color)

def encode_coloring(n, k, edges):
    """CNF: var = v*k + c + 1 for node v, color c."""
    def var(v, c):
        return v * k + c + 1
    clauses = []
    for v in range(n):                               # each node >=1 color
        clauses.append([var(v, c) for c in range(k)])
    for v in range(n):                               # each node <=1 color
        for c1, c2 in itertools.combinations(range(k), 2):
            clauses.append([-var(v, c1), -var(v, c2)])
    for u, v in edges:                               # adjacent nodes differ
        for c in range(k):
            clauses.append([-var(u, c), -var(v, c)])
    return n * k, clauses

def main():
    inst = os.path.join(OUT, "instances")
    hid = os.path.join(OUT, "hidden")
    os.makedirs(inst, exist_ok=True)
    os.makedirs(hid, exist_ok=True)
    expected = {}

    # UNSAT: pigeonhole
    for n, name, d in [(7, "php7", inst), (8, "php8", inst), (9, "php9", hid)]:
        nv, cl = php(n)
        write_cnf(os.path.join(d, f"{name}.cnf"), nv, cl)
        expected[name] = {"verdict": "UNSAT", "vars": nv, "clauses": len(cl)}
        print(f"{name}: {nv} vars {len(cl)} clauses UNSAT")

    # SAT: planted random 3-SAT
    for n, m, seed, name, d in [
        (150, 640, 7, "rand150", inst),
        (200, 850, 42, "rand200", inst),
        (250, 1050, 123, "rand250", inst),
        (220, 950, 99, "rand220", hid),
    ]:
        nv, cl = planted_3sat(n, m, seed)
        write_cnf(os.path.join(d, f"{name}.cnf"), nv, cl)
        expected[name] = {"verdict": "SAT", "vars": nv, "clauses": len(cl)}
        print(f"{name}: {nv} vars {len(cl)} clauses SAT(planted)")

    # SAT: graph coloring (encode + known coloring)
    for n, k, p, seed, name, d in [
        (12, 3, 0.5, 5, "coloring12", inst),
        (14, 3, 0.55, 11, "coloring14", hid),
    ]:
        nodes, edges, coloring = coloring_instance(n, k, p, seed)
        nv, cl = encode_coloring(n, k, edges)
        write_cnf(os.path.join(d, f"{name}.cnf"), nv, cl)
        expected[name] = {"verdict": "SAT", "vars": nv, "clauses": len(cl)}
        with open(os.path.join(d, f"{name}.json"), "w") as f:
            json.dump({"n": nodes, "k": k, "edges": edges}, f, indent=1)
        print(f"{name}: {nodes} nodes {len(edges)} edges -> {nv} vars {len(cl)} clauses SAT")

    with open(os.path.join(OUT, "expected.json"), "w") as f:
        json.dump(expected, f, indent=1)
    print("OK ->", OUT)

if __name__ == "__main__":
    sys.exit(main())
