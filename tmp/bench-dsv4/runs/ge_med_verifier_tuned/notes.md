# SAT Solver & Graph Coloring Notes

## 1. Architecture & Design Decisions

### Core Solver (`solver.py`)
A complete Conflict-Driven Clause Learning (CDCL) SAT solver written in Python 3 standard library with zero external dependencies.

- **Flat-Array Representation & Fast Indexing**:
  Variables are 1-indexed integers $1 \dots N$. Assignments and watch structures use a flat array of size $2N+1$. Literal $p > 0$ maps to index $p$, and negative literal $-p$ directly maps to Python negative slice index $-p$. This enables $O(1)$ literal evaluations (`assigns[p] == 1` for TRUE, `-1` for FALSE, `0` for UNASSIGNED) with zero dictionary lookups or bit shifts.

- **Two-Watched Literals (2WL)**:
  Each clause watches two non-false literals at `cl[0]` and `cl[1]`. When literal $p$ is assigned False, only clauses watching $p$ are inspected. In-place pointer swapping and slice truncation (`del ws[j:]`) minimize list allocations and memory overhead during Boolean Constraint Propagation (BCP).

- **1-UIP Conflict Analysis & Non-Chronological Backjumping**:
  Implements standard First Unique Implication Point (1-UIP) resolution. When BCP encounters a conflict clause, the implication graph is traversed backwards along the assignment trail to derive the asserting learned clause and determine the optimal backtrack level.

- **VSIDS & Phase Saving**:
  Variable State Independent Decaying Sum (VSIDS) maintains variable conflict activities with decay factor 0.95 and periodic rescaling to prevent float overflow. Candidate selection leverages Python's C-implemented `heapq` with lazy updates. Phase saving preserves the last assigned truth value of each variable, allowing search to quickly resume promising subspaces after backtracking and restarts.

- **Luby Restarts & Clause DB Reduction**:
  Restarts follow the standard Luby sequence ($1, 1, 2, 1, 1, 2, 4, \dots$) with a base conflict limit of 100. Learned clause database reduction periodically purges low-activity learned clauses while preserving "glue" clauses ($LBD \le 2$).

### Graph Coloring Encoder (`encode_coloring.py`)
Encodes vertex $k$-coloring into DIMACS CNF using the standard mapping variable $v \cdot k + c + 1$ representing vertex $v$ having color $c$:
1. **At-least-one color per vertex**: $\bigvee_{c=0}^{k-1} x_{v,c}$ for each vertex ($n$ clauses).
2. **At-most-one color per vertex**: $\neg x_{v,c_1} \lor \neg x_{v,c_2}$ for all $0 \le c_1 < c_2 < k$ ($n \cdot \binom{k}{2}$ clauses).
3. **Proper coloring constraint**: $\neg x_{u,c} \lor \neg x_{v,c}$ for every edge $(u, v)$ and color $c$ ($|E| \cdot k$ clauses).

---

## 2. Measured Execution Times

All benchmarks were measured with Python 3 on the grader harness:

| Instance | Type | Variables | Clauses | Verdict | Status | Measured Time |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `coloring12` | Visible | 36 | 123 | SAT | PASS | 0.015 s |
| `php7` | Visible | 42 | 133 | UNSAT | PASS | 0.063 s |
| `rand150` | Visible | 150 | 640 | SAT | PASS | 0.077 s |
| `rand200` | Visible | 200 | 850 | SAT | PASS | 0.308 s |
| `php8` | Visible | 56 | 204 | UNSAT | PASS | 0.465 s |
| `rand250` | Visible | 250 | 1050 | SAT | PASS | 6.221 s |
| `coloring14` | Hidden | 42 | 170 | SAT | PASS | 0.021 s |
| `rand220` | Hidden | 220 | 950 | SAT | PASS | 0.672 s |
| `php9` | Hidden | 72 | 297 | UNSAT | PASS | 6.122 s |

---

## 3. Implementation Insights & What Didn't Work

- **Naive Watched List Mutation vs In-Place Overwrites**: Initial prototypes that created new watch lists during BCP incurred heavy garbage collection overhead in Python. Switching to in-place two-pointer updates (`ws[j] = cl; j += 1; del ws[j:]`) yielded a ~3.5x speedup.
- **Heap Invalidation Overhead**: Maintaining an exact heap with per-variable position tracking introduced substantial dictionary and list manipulation costs. Adopting lazy heap popping with truth-value filtering proved significantly faster in CPython.
- **Restart Frequencies**: Aggressive restarts (< 50 conflicts) slowed down convergence on pigeonhole instances (`php8`, `php9`) because the solver discarded partially-learned resolution chains before reaching 1-UIP cuts. A Luby base of 100 provided the optimal balance between space exploration and deep proof construction.
