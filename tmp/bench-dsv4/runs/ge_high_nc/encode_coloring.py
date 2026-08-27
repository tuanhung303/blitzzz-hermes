#!/usr/bin/env python3
"""Part B: Graph Coloring to CNF Encoder.
Encodes graph k-coloring into DIMACS CNF (coloring.cnf),
solves it with solver.py, and writes coloring_solution.json.
"""
import json
import os
import sys

from solver import CDCLSolver, parse_cnf


def encode_graph(json_path, cnf_path):
    with open(json_path, "r") as f:
        data = json.load(f)

    n = data["n"]
    k = data["k"]
    edges = data["edges"]

    clauses = []
    # Variable for node v and color c: v * k + c + 1 (1-indexed)
    def var(v, c):
        return v * k + c + 1

    # 1. At-least-one color per node
    for v in range(n):
        clauses.append([var(v, c) for c in range(k)])

    # 2. At-most-one color per node
    for v in range(n):
        for c1 in range(k):
            for c2 in range(c1 + 1, k):
                clauses.append([-var(v, c1), -var(v, c2)])

    # 3. Adjacent nodes cannot have the same color
    for u, v in edges:
        for c in range(k):
            clauses.append([-var(u, c), -var(v, c)])

    nvars = n * k
    nclauses = len(clauses)

    with open(cnf_path, "w") as f:
        f.write(f"p cnf {nvars} {nclauses}\n")
        for cl in clauses:
            f.write(" ".join(map(str, cl)) + " 0\n")

    return n, k, edges, nvars, clauses


def solve_and_save(cnf_path, n, k, out_json_path):
    nvars, clauses = parse_cnf(cnf_path)
    solver = CDCLSolver(nvars, clauses)
    verdict, model = solver.solve()
    if verdict == "SAT":
        asn = {abs(l): l > 0 for l in model}
        colors = []
        for v in range(n):
            for c in range(k):
                if asn.get(v * k + c + 1, False):
                    colors.append(c)
                    break
        with open(out_json_path, "w") as f:
            json.dump({"colors": colors}, f, indent=1)
        return colors
    return None


def main():
    json_path = os.path.join("task", "grader", "instances", "coloring12.json")
    if len(sys.argv) > 1:
        json_path = sys.argv[1]

    cnf_path = "coloring.cnf"
    out_json = "coloring_solution.json"

    n, k, edges, nvars, clauses = encode_graph(json_path, cnf_path)
    solve_and_save(cnf_path, n, k, out_json)


if __name__ == "__main__":
    main()
