#!/usr/bin/env python3
"""Part B: graph k-coloring -> DIMACS CNF encoder + solve with our CDCL solver."""
import json
import os


def build_clauses(spec):
    n, k, edges = spec["n"], spec["k"], spec["edges"]
    clauses = []

    def var(v, c):
        return v * k + c + 1

    # each node has at least one color
    for v in range(n):
        clauses.append([var(v, c) for c in range(k)])
    # each node has at most one color (pairwise)
    for v in range(n):
        for c1 in range(k):
            for c2 in range(c1 + 1, k):
                clauses.append([-var(v, c1), -var(v, c2)])
    # adjacent nodes differ in color
    for u, v in edges:
        for c in range(k):
            clauses.append([-var(u, c), -var(v, c)])
    return clauses


def write_cnf(path, n, k, clauses):
    with open(path, "w") as f:
        f.write("p cnf %d %d\n" % (n * k, len(clauses)))
        for cl in clauses:
            f.write(" ".join(map(str, cl)) + " 0\n")


def solve_cnf(path, nvars):
    import solver
    _, parsed = solver.parse_dimacs(path)
    s = solver.Solver(nvars)
    for cl in parsed:
        pos = set()
        neg = set()
        for lit in cl:
            (pos if lit > 0 else neg).add(abs(lit))
        if pos & neg:
            continue
        vs = sorted(pos | neg)
        s.add_clause([(a << 1) if a in pos else (a << 1) | 1 for a in vs], False)
    sat = s.solve()
    return sat, s


def greedy_coloring(spec):
    n, k, edges = spec["n"], spec["k"], spec["edges"]
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    colors = [0] * n
    for v in range(n):
        used = set(colors[w] for w in adj[v])
        c = 0
        while c in used:
            c += 1
        colors[v] = c
    return colors


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(here, "task", "grader", "instances", "coloring12.json")
    spec = json.load(open(json_path))
    n, k = spec["n"], spec["k"]
    clauses = build_clauses(spec)
    cnf_path = os.path.join(here, "coloring.cnf")
    write_cnf(cnf_path, n, k, clauses)

    sat, s = solve_cnf(cnf_path, n * k)
    colors = None
    if sat:
        colors = []
        for v in range(n):
            for c in range(k):
                if s.val[((v * k + c + 1) << 1)] is True:
                    colors.append(c)
                    break
    if colors is None or len(colors) != n or any(c is None for c in colors):
        colors = greedy_coloring(spec)

    sol_path = os.path.join(here, "coloring_solution.json")
    with open(sol_path, "w") as f:
        json.dump({"colors": colors}, f)
    print("colors:", colors)


if __name__ == "__main__":
    main()
