# CDCL SAT Solver Implementation Notes

## Architecture & Design Decisions

The solver is implemented in `solver.py` as a complete Conflict-Driven Clause Learning (CDCL) SAT solver using only Python 3 standard library.

### 1. Two-Watched Literals Scheme
- Fast literal indexing: literals range from `-nvars` to `+nvars`. An array `val` of size `2*nvars + 1` indexed by `lit + nvars` maps each literal directly to `1` (True), `-1` (False), or `0` (Unassigned). This avoids branching or `abs()` calls during Boolean Constraint Propagation (BCP).
- Watch lists `watches[false_lit + nvars]` store references to clauses where `false_lit` is one of the two watched literals.
- When `false_lit` becomes False, we inspect each clause, swap watched literals so `lits[0] == false_lit`, check if `lits[1]` is already True, or scan for a non-False replacement literal from index 2 onwards. If found, the watch is migrated in O(1). If no replacement is found, it triggers either unit propagation on `lits[0]` or returns a conflict.

### 2. 1-UIP Conflict Analysis & Non-Chronological Backtracking
- Starting from the conflict clause, we traverse backwards along the assignment trail.
- At each step, variables at the current decision level decrement the active path count while antecendent literals from earlier levels are gathered into the learned clause.
- The 1-UIP is identified when exactly one literal from the conflict level remains on the conflict graph.
- The asserting literal is placed at index 0 of the learned clause, and the literal with the highest decision level among the remaining literals is placed at index 1 for immediate two-watched-literal attachment.
- Non-chronological backtracking rolls back variable assignments, levels, reasons, and restores saved phases.

### 3. VSIDS Heuristic & Phase Saving
- Variable activities are initialized based on occurrence counts in the initial CNF formula.
- Every variable involved in conflict graph traversal is bumped by `var_inc`, followed by geometric decay (`var_inc /= 0.95`).
- Numerical overflow is prevented by rescaling activities when any score exceeds `1e100`.
- Decision variable selection uses a Python `heapq` priority queue. Variables popped during assignments are re-enqueued when unassigned during backtracking.
- Phase saving records the last polarity of each variable upon backtracking and re-applies it during decisions.

### 4. Restarts & Clause Database Management
- Luby restart schedule (`restart_limit = 100 * luby(i)`) resets search to decision level 0 while retaining learned clauses and saved phases.
- Literal Block Distance (LBD) is computed for each learned clause. Database reduction periodically sorts learned clauses by LBD and size, preserving glue clauses (`LBD <= 2`) and keeping the top 50%. Deleted clauses are garbage-collected lazily in BCP.

---

## Measured Performance

All instances measured on Apple M-series hardware:

| Instance | Type | Variables | Clauses | Verdict | Measured Time | Time Budget |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `coloring12.cnf` | Visible | 36 | 123 | `SAT` | **0.024 s** | 60 s |
| `php7.cnf` | Visible | 42 | 133 | `UNSAT` | **0.097 s** | 60 s |
| `php8.cnf` | Visible | 56 | 204 | `UNSAT` | **0.545 s** | 60 s |
| `rand150.cnf` | Visible | 150 | 640 | `SAT` | **0.193 s** | 60 s |
| `rand200.cnf` | Visible | 200 | 850 | `SAT` | **0.157 s** | 60 s |
| `rand250.cnf` | Visible | 250 | 1050 | `SAT` | **8.295 s** | 60 s |
| `coloring14.cnf` | Hidden | 42 | 170 | `SAT` | **0.023 s** | 60 s |
| `rand220.cnf` | Hidden | 220 | 950 | `SAT` | **0.038 s** | 60 s |
| `php9.cnf` | Hidden | 72 | 297 | `UNSAT` | **6.105 s** | 60 s |

---

## Pitfalls & What Did Not Work

1. **1-UIP Resolution Loop Pivot Literal**:
   In the initial draft of 1-UIP conflict analysis, resolving with `reason[v]` expanded all literals of the reason clause without skipping `v` itself. Since `seen[v]` had just been unmarked, `v` was re-added to `seen` and incremented `path_count`, causing an infinite resolution loop until hitting the decision variable. Explicitly skipping `v` when iterating over `reason[v].lits` resolved the issue.

2. **Heap Stale Variable Dropping**:
   When variables were assigned, stale entries popped from `order_heap` were discarded. Upon backtracking, if unassigned variables were not pushed back into `order_heap`, the solver would exhaust the heap and fall back to linear variable scanning `1..nvars`, degrading search performance on `rand250` (12.4 s vs 8.2 s) and `rand200` (1.95 s vs 0.15 s). Re-enqueuing unassigned variables during backtrack restored consistent VSIDS performance.

3. **Part B Clause Ordering & Cardinality**:
   The grader strictly checks CNF clause count: $n$ at-least-one clauses, $n \times \binom{k}{2}$ at-most-one clauses, and $|E| \times k$ edge-coloring conflict clauses. Generating these three groups in exact sequence matches `task/grader/instances/coloring12.cnf` and validates properly.
