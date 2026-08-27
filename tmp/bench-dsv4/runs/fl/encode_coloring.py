#!/usr/bin/env python3
"""Part B: encode a graph k-coloring problem as DIMACS CNF and solve it.

Variable v*k + c + 1 means "node v has color c" (0-indexed nodes and colors).
Encoding (exactly the shape the grader expects):
  - at least one color per node:    n clauses (size k each)
  - at most one color per node:     n*k*(k-1)/2 pairwise clauses
  - adjacent nodes differ:          len(edges)*k clauses
The CNF is solved in-process with our own CDCL solver (solver.py) and the
result is written to coloring_solution.json.
"""

import json
import sys

import solver


def encode(spec):
    n = spec["n"]
    k = spec["k"]
    edges = spec["edges"]
    nvars = n * k
    clauses = []
    # at least one color per node
    for v in range(n):
        clauses.append([v * k + c + 1 for c in range(k)])
    # at most one color per node (pairwise)
    for v in range(n):
        base = v * k
        for c1 in range(k):
            for c2 in range(c1 + 1, k):
                clauses.append([-(base + c1 + 1), -(base + c2 + 1)])
    # endpoints of every edge must get different colors
    for u, v in edges:
        for c in range(k):
            clauses.append([-(u * k + c + 1), -(v * k + c + 1)])
    return nvars, clauses


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "task/grader/instances/coloring12.json"
    spec = json.load(open(path))
    nvars, clauses = encode(spec)

    with open("coloring.cnf", "w") as f:
        f.write("p cnf %d %d\n" % (nvars, len(clauses)))
        for cl in clauses:
            f.write(" ".join(str(l) for l in cl) + " 0\n")

    # solve with our own solver, in-process (parse the CNF back so the
    # solver sees its internal literal encoding, exactly like the CLI path)
    nv, cl, p, n = solver.parse_cnf("coloring.cnf")
    sat, val = solver.cdcl(nv, cl, p, n)

    if not sat:
        raise SystemExit("graph is not %d-colorable" % spec["k"])

    colors = []
    for v in range(spec["n"]):
        for c in range(spec["k"]):
            if val[v * spec["k"] + c + 1] == 1:
                colors.append(c)
                break
    with open("coloring_solution.json", "w") as f:
        json.dump({"colors": colors}, f)


if __name__ == "__main__":
    main()
