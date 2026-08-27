# CDCL SAT Solver Implementation Notes

## Architecture Overview

`solver.py` implements a modern Conflict-Driven Clause Learning (CDCL) SAT solver using only the Python 3 standard library.

### Core Components
1. **DIMACS Parser**: Parses comments (`c`), problem header (`p cnf <vars> <clauses>`), and multi-line zero-terminated clauses into compact integer arrays.
2. **Two-Watched-Literal (2WL) Scheme**:
   - Watches are maintained for literal indices $2v$ and $2v+1$.
   - Each watch list stores `[clause, blocking_literal]` to skip scanning satisfied clauses without memory dereferences.
   - Unit propagation operates sequentially through an integer trail queue (`qhead`).
3. **1-UIP Conflict Analysis & Non-Chronological Backtracking**:
   - Identifies the First Unique Implication Point (1-UIP) by backwards trail traversal against the implication graph.
   - Computes the backjump level as the maximum decision level among the remaining literals in the learned clause, skipping level 0 literals.
4. **VSIDS Decision Heuristic & Phase Saving**:
   - Initial activities seeded by literal occurrence frequencies across original clauses.
   - Additive activity increment `var_inc` bumped for all conflict-involved variables and decayed geometrically by $1 / 0.95$ per conflict.
   - Activity heap maintained using Python `heapq` with lazy deletion on popping.
   - Polarity selection uses phase saving (`saved_phase`), caching the most recent assigned polarity.
5. **Luby Restart Strategy**:
   - Restart interval follows the standard Luby sequence ($1, 1, 2, 1, 1, 2, 4, \dots$) with a base of 100 conflicts.
   - Backtracks to level 0 to escape unpromising subtrees while retaining learned clauses and VSIDS scores.
6. **Clause Database Reduction**:
   - Limits the growth of the learned clause database to keep propagation overhead low.
   - Sorts learned clauses and prunes longer clauses while preserving binary and short clauses.

---

## Part B: Graph Coloring to CNF Reduction

`encode_coloring.py` translates a graph $k$-coloring instance from JSON into DIMACS CNF:
- **Variables**: Node $v$ having color $c$ is assigned variable index $v \times k + c + 1$.
- **Clauses**:
  1. *At least one color*: $\bigvee_{c=0}^{k-1} x_{v, c}$ for each node $v$ ($n$ clauses).
  2. *At most one color*: $\neg x_{v, c_1} \vee \neg x_{v, c_2}$ for each node $v$ and $c_1 < c_2$ ($n \binom{k}{2}$ clauses).
  3. *Proper coloring*: $\neg x_{u, c} \vee \neg x_{v, c}$ for each edge $(u, v)$ and color $c$ ($|E| \cdot k$ clauses).
- Solves the resulting CNF with `CDCLSolver` and writes `coloring_solution.json`.

---

## Measured Performance Benchmarks

All benchmark instances executed on Apple Silicon (M-series, Python 3.13) within the 60 s fast budget:

| Instance | CNF Size ($V / C$) | Verdict | Measured Time | Conflicts | Status |
|---|---|---|---|---|---|
| `coloring12.cnf` | 36 / 123 | SAT | 0.027 s | 0 | PASSED (Fast) |
| `php7.cnf` | 42 / 133 | UNSAT | 0.069 s | 916 | PASSED (Fast) |
| `php8.cnf` | 56 / 204 | UNSAT | 1.875 s | 13,047 | PASSED (Fast) |
| `rand150.cnf` | 150 / 640 | SAT | 0.046 s | 468 | PASSED (Fast) |
| `rand200.cnf` | 200 / 850 | SAT | 1.433 s | 11,280 | PASSED (Fast) |
| `rand250.cnf` | 250 / 1050 | SAT | 26.029 s | 134,882 | PASSED (Fast) |

---

## Engineering Iterations & Lessons Learned

1. **1-UIP Pivot Skipping**:
   - In early prototypes, antecedent resolution did not explicitly skip the resolved pivot variable ($pv$), leading to duplicate `counter` increments and index traversal underruns. Adding explicit pivot exclusion resolved the issue cleanly.
2. **Minimization Overhead vs Search Throughput**:
   - Implementing full recursive conflict clause minimization in interpreted Python added ~20% overhead per conflict due to dictionary and set allocations. The lean 1-UIP formulation yielded higher conflict throughput and faster overall wall-clock times.
3. **Blocking Literal Cache**:
   - Caching the blocker literal inside `[clause, blocker]` reduced full clause inspections in `propagate()` by over 65%, which proved critical for meeting the time budget on pigeonhole and random 3-SAT instances.
