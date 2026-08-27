#!/usr/bin/env python3
import json
import os
import sys
from solver import Solver, parse_dimacs

def encode(json_path="task/grader/instances/coloring12.json", cnf_path="coloring.cnf"):
    with open(json_path, "r") as f:
        data = json.load(f)
        
    n = data["n"]
    k = data["k"]
    edges = data["edges"]
    
    nvars = n * k
    clauses = []
    
    # 1. At least one color per node
    for v in range(n):
        clauses.append([v * k + c + 1 for c in range(k)])
        
    # 2. At most one color per node
    for v in range(n):
        for c1 in range(k):
            for c2 in range(c1 + 1, k):
                clauses.append([-(v * k + c1 + 1), -(v * k + c2 + 1)])
                
    # 3. Adjacent nodes must have different colors
    for u, v in edges:
        for c in range(k):
            clauses.append([-(u * k + c + 1), -(v * k + c + 1)])
            
    # Write to DIMACS CNF
    with open(cnf_path, "w") as f:
        f.write(f"p cnf {nvars} {len(clauses)}\n")
        for cl in clauses:
            f.write(" ".join(map(str, cl)) + " 0\n")
            
    return n, k, edges, cnf_path

def main():
    json_path = sys.argv[1] if len(sys.argv) > 1 else "task/grader/instances/coloring12.json"
    cnf_path = "coloring.cnf"
    n, k, edges, cnf_path = encode(json_path, cnf_path)
    
    # Solve with solver
    nvars, raw_clauses = parse_dimacs(cnf_path)
    solver = Solver(nvars, raw_clauses)
    verdict, model = solver.solve()
    
    if verdict == "SAT" and model:
        asn = {abs(l): (l > 0) for l in model}
        colors = []
        for v in range(n):
            node_color = None
            for c in range(k):
                var = v * k + c + 1
                if asn.get(var, False):
                    node_color = c
                    break
            colors.append(node_color)
            
        with open("coloring_solution.json", "w") as f:
            json.dump({"colors": colors}, f, indent=1)
    else:
        print("UNSAT / Failed to solve coloring instance")

if __name__ == "__main__":
    main()
