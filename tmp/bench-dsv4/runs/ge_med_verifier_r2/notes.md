# CDCL SAT Solver Implementation Notes

## Architecture & Design Decisions

The solver (`solver.py`) is implemented from scratch in pure Python 3 using standard library modules only (`sys`, `heapq`).

### 1. Two-Watched Literals (2WL)
- Literals are mapped directly to dense 0-based integer indices (`lit > 0 -> 2*v`, `lit < 0 -> 2*v + 1`), allowing constant-time negation via bitwise XOR (`lit ^ 1`).
- Clauses store internal literal indices, eliminating runtime object creation, sign checks, and multiplications.
- The watch list `watches[lit]` tracks clause indices watching `lit`. During boolean constraint propagation (BCP), only clauses watching falsified literals are examined.
- Replaced watches update in-place without scanning non-watched literals when satisfied.

### 2. Conflict Analysis & Clause Learning (1-UIP)
- First Unique Implication Point (1-UIP) conflict analysis walks the implication graph backwards starting from the falsified conflict clause.
- A `seen` boolean array tracks visited decision-level literals.
- Backtrack level is dynamically computed as the highest decision level among antecedent literals in the learned clause (or 0 for unit learned clauses).
- The asserting 1-UIP literal is placed at index 0 and the highest-level antecedent at index 1 for immediate two-watched literal registration upon backtracking.

### 3. VSIDS Decision Heuristic & Phase Saving
- Variables maintain floating-point activity scores initialized to 0.0 and incremented on every conflict participation (`var_inc`).
- Activities decay via `var_inc /= 0.95`, with geometric rescaling on numeric overflow.
- A binary heap with lazy invalidation selects highest-activity unassigned variables in logarithmic time.
- Phase saving records the last polarity of assigned variables to preserve previously explored satisfying subspaces across restarts.

### 4. Restarts & Clause Database Reduction
- Restarts follow the Luby sequence (`restart_base = 50`), resetting the decision level to 0 while preserving learned clauses, phase memories, and VSIDS scores.
- Clause database reduction computes Literal Block Distance (LBD) for each learned clause. Non-locked clauses with LBD > 2 are pruned periodically when the learned clause database exceeds dynamically expanding limits.

### 5. Part B: Graph Coloring Reduction (`encode_coloring.py`)
- Maps graph coloring constraints for $n$ nodes and $k$ colors to CNF:
  - At-least-one color per vertex: $n$ clauses of length $k$.
  - At-most-one color per vertex: $n \cdot \frac{k(k-1)}{2}$ binary clauses.
  - Conflict edges: $|E| \cdot k$ binary clauses enforcing distinct adjacent colors.
- Produces `coloring.cnf` and executes the solver to export `coloring_solution.json`.

---

## Measured Benchmark Timings

Evaluated using `task/grader/grader.py` (timeout budget 60 s per instance):

| Instance | Variables | Clauses | Expected | Result | Measured Time | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `coloring12.cnf` | 36 | 123 | SAT | SAT | 0.023 s | PASS |
| `php7.cnf` | 42 | 133 | UNSAT | UNSAT | 0.051 s | PASS |
| `php8.cnf` | 56 | 204 | UNSAT | UNSAT | 0.430 s | PASS |
| `rand150.cnf` | 150 | 640 | SAT | SAT | 0.060 s | PASS |
| `rand200.cnf` | 200 | 850 | SAT | SAT | 0.475 s | PASS |
| `rand250.cnf` | 250 | 1050 | SAT | SAT | 19.306 s | PASS |
| `coloring14.cnf` (hidden) | 42 | 170 | SAT | SAT | 0.030 s | PASS |
| `php9.cnf` (hidden) | 72 | 297 | UNSAT | UNSAT | 21.842 s | PASS |
| `rand220.cnf` (hidden) | 220 | 950 | SAT | SAT | 2.040 s | PASS |

---

## Engineering Challenges & Failed Attempts

1. **Conflict Resolution Loop Indexing**: Initial 1-UIP resolution did not skip the implied literal when scanning `reason[v]`, which caused re-adding visited variables back into the resolution counter and corrupting conflict levels. Fixed by explicitly excluding the resolved variable.
2. **Backtrack Level Invariant**: An early aggressive clause minimization attempt removed literals without re-synchronizing the backtrack level against the updated clause literals, resulting in desynchronized 2WL watches. Corrected by strictly computing the backtrack level from the maximum level among antecedent literals in the final learned clause.
3. **Literal Index Representation**: Initial implementation converted between integers and absolute values on each watch inspection. Profiling revealed that converting clauses to dense 0-based literal indices (`2*v`, `2*v+1`) up-front yielded a 2.5x speedup across random 3-SAT instances.
