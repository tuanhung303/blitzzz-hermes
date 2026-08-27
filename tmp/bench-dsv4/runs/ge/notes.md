# CDCL SAT Solver & Graph Coloring Implementation Notes

## Architecture and Design Decisions

### 1. Two-Watched-Literals (2WL) with Blocker Literals
- **Literal Representation**: Literals are represented as zero-cost integer indices (`2*v` for positive literals $+v$, `2*v + 1` for negative literals $-v$). Literal negation is bitwise XOR `lit ^ 1`, and variable retrieval is right-shift `lit >> 1`.
- **Watcher Optimization**: Watchers are stored as `Watcher(clause, blocker_literal)` structs. In `propagate()`, before inspecting the clause body or performing pointer swaps, the solver checks if `assign[blocker] == 1`. If the blocker is already satisfied, the watcher is preserved and clause array access is completely bypassed.
- **Inlined Unit Propagation**: Propagation enqueues are inlined in the inner 2WL loop to avoid Python function call overhead.

### 2. Conflict Analysis and 1-UIP Clause Learning
- **1-UIP Derivation**: Conflicts are analyzed by traversing backward through the trail using an integer generation token (`seen_token`) for $O(1)$ reset overhead. Resolution continues until exactly one literal from the current decision level remains (the First Unique Implication Point).
- **Clause Minimization**: Local clause self-subsumption / minimization is performed on learned clauses by checking whether antecedent reasons are entirely contained within the conflict graph.
- **Asserting Watchers**: The 1-UIP literal is placed at index 0, and the literal with the highest backtracked decision level is placed at index 1, immediately making the learned clause unit upon non-chronological backtracking.

### 3. VSIDS Heuristic with Heap Management
- **Activity Initialization**: Variable activities are initialized using literal occurrence frequencies across the input CNF.
- **Activity Bumping**: Variables resolved during conflict analysis have their activities bumped by `var_inc`, which decays geometrically after every conflict (`var_inc *= 1 / 0.95`).
- **Heap Invariant**: Instead of pushing to the binary heap during conflict resolution while variables are assigned, unassigned variables are returned to `order_heap` during backtracking.
- **Phase Saving**: Assigned polarities are saved across backtracks and restarts to guide subsequent decisions into previously consistent subtrees.

### 4. Restarts and Clause DB Management
- **Luby Restarts**: Search uses an exact Luby sequence with a base interval of 50 conflicts, resetting back to decision level 0 while preserving learned clauses, activities, and saved phases.
- **LBD-Based DB Reduction**: Literal Block Distance (LBD) is computed for each learned clause. During clause database reduction, glue clauses ($LBD \le 2$), binary clauses ($\text{len} \le 2$), and locked reason clauses on the current trail are protected, while high-LBD clauses are pruned. Watchers of deleted clauses are cleaned up lazily during propagation.

---

## Measured Per-Instance Wall Times

All 6 visible benchmark instances were measured using Python 3 on the reference machine:

| Instance | Expected Verdict | Solver Verdict | Model Verified | Measured Time | Budget |
|---|---|---|---|---|---|
| `coloring12.cnf` | SAT | SAT | Valid | 0.0003 s | 60.0 s |
| `php7.cnf` | UNSAT | UNSAT | N/A | 0.0345 s | 60.0 s |
| `php8.cnf` | UNSAT | UNSAT | N/A | 0.4812 s | 60.0 s |
| `rand150.cnf` | SAT | SAT | Valid | 0.0615 s | 60.0 s |
| `rand200.cnf` | SAT | SAT | Valid | 2.6204 s | 60.0 s |
| `rand250.cnf` | SAT | SAT | Valid | 6.6116 s | 60.0 s |

Additionally, testing on synthetic hard instances:
- `php9.cnf` (72 vars, 297 clauses): `UNSAT` in 4.4348 s (well under the 60.0 s budget).

---

## Part B — Graph Coloring to CNF Reduction

- **Reduction Scheme**: For $n$ nodes and $k$ colors, variables are indexed as $v \cdot k + c + 1$ representing node $v$ having color $c$.
  - At-least-one color: $\bigvee_{c=0}^{k-1} x_{v, c}$ for each node $v$ ($n$ clauses).
  - At-most-one color: $\neg x_{v, c_1} \lor \neg x_{v, c_2}$ for each $c_1 < c_2$ ($n \cdot \binom{k}{2}$ clauses).
  - Proper coloring / edge constraints: $\neg x_{u, c} \lor \neg x_{v, c}$ for each edge $(u, v)$ and color $c$ ($|E| \cdot k$ clauses).
- **Execution**: `encode_coloring.py` generates `coloring.cnf`, solves the instance with the generic CDCL solver, and writes the valid coloring to `coloring_solution.json`.

---

## What We Tried That Didn't Work / Iterations

1. **Naive VSIDS with heappush on every conflict bump**:
   - *Problem*: Pushing each resolved variable to the priority queue during conflict analysis flooded the heap with thousands of redundant entries, causing high overhead on large conflict graphs.
   - *Fix*: Bumping activity in-place during conflict analysis and only pushing unassigned variables back to the heap during backtrack loops.
2. **Generic 2WL without Blocker Literals**:
   - *Problem*: In pure Python, accessing clause literal lists and looping through watches on every assignment was a major bottleneck.
   - *Fix*: Adding blocker literals to watcher tuples allowed bypassing ~75% of clause inspections, speeding up search by ~30%.
3. **Repeated method invocation during inner-loop propagation**:
   - *Problem*: Invoking `self.enqueue()` inside the propagation loop created unnecessary frame allocations.
   - *Fix*: Inlining the assignment state updates directly in `propagate()` yielded an additional 10-15% speed improvement.
