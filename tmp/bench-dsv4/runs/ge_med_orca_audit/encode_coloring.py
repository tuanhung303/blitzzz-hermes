#!/usr/bin/env python3
import json
import os
import sys
from solver import parse_cnf, CDCLSolver

def encode_graph_coloring(json_path, cnf_path):
    with open(json_path, "r") as f:
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
                
    # 3. Adjacent nodes have different colors
    for u, v in edges:
        for c in range(k):
            clauses.append([-(u * k + c + 1), -(v * k + c + 1)])
            
    with open(cnf_path, "w") as f:
        f.write(f"p cnf {num_vars} {len(clauses)}\n")
        for cl in clauses:
            f.write(" ".join(map(str, cl)) + " 0\n")
            
    return spec, num_vars, clauses

def main():
    json_path = os.path.join("task", "grader", "instances", "coloring12.json")
    if not os.path.exists(json_path):
        json_path = "coloring12.json"
        
    cnf_path = "coloring.cnf"
    sol_path = "coloring_solution.json"
    
    spec, num_vars, clauses = encode_graph_coloring(json_path, cnf_path)
    
    # Solve coloring.cnf
    solver = CDCLSolver(num_vars, clauses)
    verdict, model = solver.solve()
    
    if verdict != "SAT" or model is None:
        print("Failed to solve coloring.cnf", file=sys.stderr)
        sys.exit(1)
        
    asn = {abs(l): l > 0 for l in model}
    colors = []
    for v in range(spec["n"]):
        for c in range(spec["k"]):
            if asn.get(v * spec["k"] + c + 1, False):
                colors.append(c)
                break
                
    with open(sol_path, "w") as f:
        json.dump({"colors": colors}, f, indent=1)
        
    print(f"Encoded and solved: {len(colors)} nodes colored with {spec['k']} colors.")

if __name__ == "__main__":
    main()
