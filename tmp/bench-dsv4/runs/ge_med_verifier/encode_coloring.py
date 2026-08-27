#!/usr/bin/env python3
import json
import os
import sys

def encode_and_solve():
    input_json = "task/grader/instances/coloring12.json"
    if len(sys.argv) > 1:
        input_json = sys.argv[1]
    
    with open(input_json, "r") as f:
        data = json.load(f)
        
    n = data["n"]
    k = data["k"]
    edges = data["edges"]
    
    nvars = n * k
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
                
    # 3. Adjacent nodes have different colors
    for u, v in edges:
        for c in range(k):
            clauses.append([-(u * k + c + 1), -(v * k + c + 1)])
            
    # Write coloring.cnf
    with open("coloring.cnf", "w") as f:
        f.write(f"p cnf {nvars} {len(clauses)}\n")
        for cl in clauses:
            f.write(" ".join(map(str, cl)) + " 0\n")
            
    # Solve using solver.py
    from solver import parse_cnf, solve
    nvars_cnf, cnf_clauses = parse_cnf("coloring.cnf")
    verdict, model = solve(nvars_cnf, cnf_clauses)
    
    if verdict == "SAT":
        asn = {abs(l): (l > 0) for l in model}
        colors = []
        for v in range(n):
            node_color = None
            for c in range(k):
                if asn.get(v * k + c + 1, False):
                    node_color = c
                    break
            colors.append(node_color)
            
        sol = {"colors": colors}
        with open("coloring_solution.json", "w") as f:
            json.dump(sol, f, indent=1)
        print("Coloring solved and written to coloring_solution.json")
    else:
        print("UNSAT - could not color graph")

if __name__ == "__main__":
    encode_and_solve()
