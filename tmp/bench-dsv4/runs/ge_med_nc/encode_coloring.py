#!/usr/bin/env python3
import json
import os
import sys

def main():
    json_path = os.path.join("task", "grader", "instances", "coloring12.json")
    if not os.path.exists(json_path):
        json_path = sys.argv[1] if len(sys.argv) > 1 else "coloring12.json"
    
    with open(json_path, "r") as f:
        data = json.load(f)
        
    n = data["n"]
    k = data["k"]
    edges = data["edges"]
    
    num_vars = n * k
    clauses = []
    
    # 1. At least one color per vertex
    for v in range(n):
        clauses.append([v * k + c + 1 for c in range(k)])
        
    # 2. At most one color per vertex
    for v in range(n):
        for c1 in range(k):
            for c2 in range(c1 + 1, k):
                clauses.append([-(v * k + c1 + 1), -(v * k + c2 + 1)])
                
    # 3. Adjacent vertices cannot share the same color
    for u, v in edges:
        for c in range(k):
            clauses.append([-(u * k + c + 1), -(v * k + c + 1)])
            
    with open("coloring.cnf", "w") as f:
        f.write(f"p cnf {num_vars} {len(clauses)}\n")
        for cl in clauses:
            f.write(" ".join(str(lit) for lit in cl) + " 0\n")

if __name__ == "__main__":
    main()
