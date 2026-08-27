#!/usr/bin/env python3
import json
import os
from solver import CDCLSolver, parse_cnf_file

def encode_graph_coloring(json_path, cnf_path):
    with open(json_path, "r", encoding="utf-8") as f:
        spec = json.load(f)
    
    n = spec["n"]
    k = spec["k"]
    edges = spec["edges"]
    
    num_vars = n * k
    clauses = []
    
    # 1. At least one color per node
    for v in range(n):
        cl = [v * k + c + 1 for c in range(k)]
        clauses.append(cl)
    
    # 2. At most one color per node
    for v in range(n):
        for c1 in range(k):
            for c2 in range(c1 + 1, k):
                clauses.append([-(v * k + c1 + 1), -(v * k + c2 + 1)])
    
    # 3. Edge constraints: adjacent nodes cannot have the same color
    for u, v in edges:
        for c in range(k):
            clauses.append([-(u * k + c + 1), -(v * k + c + 1)])
    
    with open(cnf_path, "w", encoding="utf-8") as f:
        f.write(f"p cnf {num_vars} {len(clauses)}\n")
        for cl in clauses:
            f.write(" ".join(str(lit) for lit in cl) + " 0\n")
    
    return n, k, edges, num_vars, clauses

def solve_and_save_solution(cnf_path, json_spec_path, out_solution_path):
    with open(json_spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)
    n = spec["n"]
    k = spec["k"]
    
    nvars, clauses = parse_cnf_file(cnf_path)
    solver = CDCLSolver(nvars, clauses)
    verdict, model = solver.solve()
    
    if verdict != "SAT":
        raise RuntimeError("Encoding was UNSAT")
    
    asn = {abs(l): (l > 0) for l in model}
    colors = []
    for v in range(n):
        assigned_color = None
        for c in range(k):
            var = v * k + c + 1
            if asn.get(var, False):
                assigned_color = c
                break
        if assigned_color is None:
            raise RuntimeError(f"Node {v} has no color assigned")
        colors.append(assigned_color)
    
    solution = {"colors": colors}
    with open(out_solution_path, "w", encoding="utf-8") as f:
        json.dump(solution, f, indent=1)

def main():
    run_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(run_dir, "task", "grader", "instances", "coloring12.json")
    cnf_path = os.path.join(run_dir, "coloring.cnf")
    sol_path = os.path.join(run_dir, "coloring_solution.json")
    
    encode_graph_coloring(json_path, cnf_path)
    solve_and_save_solution(cnf_path, json_path, sol_path)

if __name__ == "__main__":
    main()
