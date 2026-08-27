#!/usr/bin/env python3
import json
import os
import sys

def encode_graph_coloring(input_json_path, output_cnf_path):
    with open(input_json_path, 'r', encoding='utf-8') as f:
        spec = json.load(f)
        
    n = spec["n"]
    k = spec["k"]
    edges = spec["edges"]
    
    # Variable encoding:
    # Node v (0 <= v < n), Color c (0 <= c < k)
    # Variable index = v * k + c + 1
    
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
            
    nvars = n * k
    nclauses = len(clauses)
    
    with open(output_cnf_path, 'w', encoding='utf-8') as f:
        f.write(f"p cnf {nvars} {nclauses}\n")
        for cl in clauses:
            f.write(" ".join(str(lit) for lit in cl) + " 0\n")

def main():
    json_path = os.path.join("task", "grader", "instances", "coloring12.json")
    cnf_path = "coloring.cnf"
    encode_graph_coloring(json_path, cnf_path)

if __name__ == "__main__":
    main()
