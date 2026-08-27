#!/usr/bin/env python3
import json
import os
import sys
from solver import CDCLSolver

def encode_and_solve(json_path="task/grader/instances/coloring12.json", cnf_path="coloring.cnf", sol_path="coloring_solution.json"):
    if not os.path.exists(json_path):
        # Fallback search
        base_dir = os.path.dirname(os.path.abspath(__file__))
        alt_path = os.path.join(base_dir, "task", "grader", "instances", "coloring12.json")
        if os.path.exists(alt_path):
            json_path = alt_path

    with open(json_path, "r") as f:
        spec = json.load(f)

    n = spec["n"]
    k = spec["k"]
    edges = spec["edges"]

    nvars = n * k
    clauses = []

    # 1. Each node has at least one color
    for v in range(n):
        clauses.append([v * k + c + 1 for c in range(k)])

    # 2. Each node has at most one color
    for v in range(n):
        for c1 in range(k):
            for c2 in range(c1 + 1, k):
                clauses.append([-(v * k + c1 + 1), -(v * k + c2 + 1)])

    # 3. Adjacent nodes have different colors
    for u, v in edges:
        for c in range(k):
            clauses.append([-(u * k + c + 1), -(v * k + c + 1)])

    # Write DIMACS CNF
    with open(cnf_path, "w") as f:
        f.write(f"p cnf {nvars} {len(clauses)}\n")
        for cl in clauses:
            f.write(" ".join(map(str, cl)) + " 0\n")

    # Solve with CDCL solver
    solver = CDCLSolver(nvars, [list(cl) for cl in clauses])
    status, model = solver.solve()
    if status == "SAT":
        asn = {abs(lit): (lit > 0) for lit in model}
        colors = []
        for v in range(n):
            node_color = None
            for c in range(k):
                var_num = v * k + c + 1
                if asn.get(var_num, False):
                    node_color = c
                    break
            colors.append(node_color)
        
        with open(sol_path, "w") as f:
            json.dump({"colors": colors}, f, indent=2)
        return True
    else:
        print("UNSAT")
        return False

if __name__ == "__main__":
    encode_and_solve()
