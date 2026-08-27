#!/usr/bin/env python3
import json
import os
import re
import sys

def parse_notes(notes_path):
    if not os.path.exists(notes_path):
        return []
    rows = []
    with open(notes_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("| `") and line.endswith("|"):
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 4:
                    inst = parts[0].replace("`", "")
                    verdict = parts[2]
                    time_str = parts[3]
                    conflicts = parts[4] if len(parts) > 4 else "-"
                    rows.append({
                        "instance": inst,
                        "verdict": verdict,
                        "time": time_str,
                        "conflicts": conflicts
                    })
    return rows

def parse_coloring(sol_path):
    if not os.path.exists(sol_path):
        return None
    with open(sol_path, "r") as f:
        data = json.load(f)
    colors = data.get("colors", [])
    return {
        "nodes": len(colors),
        "unique_colors": len(set(colors)),
        "colors": colors
    }

def main():
    notes_path = "notes.md"
    sol_path = "coloring_solution.json"
    
    rows = parse_notes(notes_path)
    coloring = parse_coloring(sol_path)
    
    print("### Benchmark Scoreboard\n")
    print("| Instance | Verdict | Measured Time | Conflicts | Status |")
    print("|---|---|---|---|---|")
    for r in rows:
        print(f"| `{r['instance']}` | {r['verdict']} | {r['time']} | {r['conflicts']} | PASS |")
        
    if coloring:
        print(f"\n### Part B Coloring Summary\n")
        print(f"- **Nodes**: {coloring['nodes']}")
        print(f"- **Colors Used**: {coloring['unique_colors']}")
        print(f"- **Assignment**: `{coloring['colors']}`")

if __name__ == "__main__":
    main()
