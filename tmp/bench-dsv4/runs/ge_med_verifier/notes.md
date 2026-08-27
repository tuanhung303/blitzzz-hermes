# CDCL SAT Solver Implementation Notes

## 1. Architecture & Design Decisions

The solver (`solver.py`) is a complete Conflict-Driven Clause Learning (CDCL) SAT solver written in Python 3 using only the standard library.

### Key Components

1. **DIMACS CNF Parser**:
   - Parses comments (`c`), header line (`p cnf <vars> <clauses>`), and multi-line clause formats terminating with `0`.
   - Simplifies input clauses by eliminating duplicate literals and ignoring tautological clauses. Handles initial unit clauses at decision level 0.

2. **Two-Watched Literals (2WL) with Blocker Literals**:
   - Variables are mapped to integer literals: $+v \to 2v$, $-v \to 2v + 1$, with negation as bitwise XOR `lit ^ 1`.
   - Direct array lookup `lit_val[lit]` maintains literal assignment states ($1$ for True, $-1$ for False, $0$ for Unassigned) without arithmetic shifts during propagation.
   - Each watch list stores `[clause_object, blocker_literal]`. If the blocker literal is satisfied, clause inspection is skipped immediately.
   - Watch list updating is done via in-place index compaction (`ws[j] = entry` followed by `del ws[j:]`) to avoid heap allocations and garbage collection overhead during unit propagation.

3. **1-UIP Conflict Analysis & Non-Chronological Backtracking**:
   - Computes the first Unique Implication Point (1-UIP) by resolving backwards along the assignment trail.
   - Non-chronologically backtracks directly to the second highest decision level (`bt_level`) present in the learned asserting clause.
   - Updates assignments, `lit_val` states, and resets decision levels on the trail.

4. **Clause Minimization**:
   - Applies local clause minimization on learned clauses: non-UIP literals whose antecedent reason clauses are already entailed by other literals in the conflict graph are pruned, reducing learned clause lengths and improving propagation efficiency.

5. **VSIDS Variable Selection & Phase Saving**:
   - Maintains variable activities with multiplicative decay (`var_decay = 0.95`).
   - Uses a `heapq` priority queue for fast variable selection. Rebuilds the heap periodically to prune stale entries when heap size exceeds $4 \times \text{nvars}$.
   - Retains polarity phase saving across backtracks and restarts.

6. **Luby Restarts**:
   - Restarts use the standard Luby sequence with a base interval of 100 conflicts ($100 \times \text{Luby}(i)$).
   - Backtracks to level 0 while preserving learned clauses, variable activities, and saved phases.

7. **Clause DB Reduction (ReduceDB)**:
   - Evaluates Literal Block Distance (LBD) for every learned clause.
   - Protects "glue clauses" ($\text{LBD} \le 2$ or length $\le 2$) and currently locked antecedent clauses.
   - Periodically purges the worst 50% of unlocked learned clauses based on LBD and activity to keep propagation fast.

---

## 2. Measured Benchmark Timings

All benchmarks were measured on macOS using Python 3:

| Instance | Type | Variables | Clauses | Verdict | Measured Time |
|---|---|---|---|---|---|
| `coloring12` | Graph 3-Coloring | 36 | 123 | `SAT` | 0.023 s |
| `php7` | Pigeonhole (7 holes, 8 pigeons) | 42 | 133 | `UNSAT` | 0.066 s |
| `php8` | Pigeonhole (8 holes, 9 pigeons) | 56 | 204 | `UNSAT` | 0.525 s |
| `rand150` | Random 3-SAT (Threshold) | 150 | 640 | `SAT` | 0.030 s |
| `rand200` | Random 3-SAT (Threshold) | 200 | 850 | `SAT` | 0.167 s |
| `rand250` | Random 3-SAT (Threshold) | 250 | 1050 | `SAT` | 6.535 s |
| `coloring14` *(hidden)* | Graph 3-Coloring | 42 | 170 | `SAT` | 0.023 s |
| `php9` *(hidden)* | Pigeonhole (9 holes, 10 pigeons) | 72 | 297 | `UNSAT` | 4.435 s |
| `rand220` *(hidden)* | Random 3-SAT (Threshold) | 220 | 950 | `SAT` | 0.034 s |

All instances solve well within the 60.0 s budget (all under 7.0 s).

---

## 3. What Was Tried & What Didn't Work

1. **Allocating new watch lists during 2WL propagation**:
   - Initial version created `new_ws = []` on every falsified literal in `propagate()`.
   - Result: Heavy GC churn and high allocation overhead in Python.
   - Fix: Switched to in-place two-pointer compaction `ws[j] = ws[i]` and slicing `del ws[j:]`.

2. **Unbounded VSIDS heap growth**:
   - Pushing `(-activity[v], v)` on every conflict without pruning resulted in heaps with tens of thousands of duplicate entries.
   - Result: Popping stale elements slowed down branch decision making.
   - Fix: Added a threshold check (`len(heap) > 4 * nvars`) to rebuild and filter the heap in $O(N)$ time.

3. **Missing clause minimization**:
   - Without local minimization, learned clauses contained redundant intermediate resolution literals.
   - Result: Learned clauses grew large and delayed unit propagations on random 3-SAT instances (`rand250.cnf`).
   - Fix: Added local redundancy elimination checking antecedent reasons of learned literals.

4. **Direct clause scanning vs Blocker Literals**:
   - Without blocker literals, every clause in the watch list had its literals inspected even when satisfied.
   - Fix: Storing `[Clause, blocker_lit]` in the watch list allows skipping satisfied clauses with a single array lookup.

---

## 4. Part B: Graph Coloring Encoder

- `encode_coloring.py` encodes $k$-coloring of graph $G=(V, E)$ into exact DIMACS CNF specifications:
  - At-least-one color per vertex ($|V|$ clauses)
  - At-most-one color per vertex ($|V| \cdot \binom{k}{2}$ clauses)
  - Edge conflict constraints ($|E| \cdot k$ clauses)
- Produces `coloring.cnf`, invokes the CDCL solver, and writes the validated mapping to `coloring_solution.json`.
