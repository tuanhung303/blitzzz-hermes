# CDCL SAT Solver + Graph-Coloring Encoder — Design Notes

## Architecture

`solver.py` is a from-scratch CDCL (conflict-driven clause learning) SAT solver,
stdlib only. Core data structures and algorithm:

- **DIMACS parser**: handles `c` comments, `p cnf` header, multi-line clauses,
  and a `%` end-of-file marker. Tautologies (a var and its negation in one
  clause) are dropped; duplicate literals are collapsed.
- **Literal encoding**: literal `v` -> `2*v`, literal `-v` -> `2*v+1`, so
  `var = lit>>1`, negation = `lit^1`, and sign = `lit&1`. This makes all the
  hot-path operations O(1) integer ops.
- **Two-watched literals**: each clause keeps its two watched literals in
  positions 0 and 1; per-literal watch lists let propagation visit only clauses
  whose watched literal just became false (no full-clause scans).
- **VSIDS decision heuristic**: per-variable activity, bumped for every variable
  that appears in conflict analysis, with geometric decay (`var_decay = 0.95`)
  and periodic rescaling. A binary heap keeps the max-activity unassigned
  variable at the top (lazy deletion + rebuild-on-empty for completeness).
- **Phase saving**: each variable remembers its last polarity and reuses it.
- **1-UIP conflict analysis**: resolves the conflict clause against reason
  clauses along the trail until exactly one literal from the current decision
  level remains, producing an asserting clause and a non-chronological
  backjump level.
- **Clause learning + non-chronological backtracking**: the learned clause's
  asserting (UIP) literal is watched and immediately assigned after the
  backjump.
- **Restarts**: Luby sequence with base 64 conflicts.
- **Clause deletion**: when learned clauses exceed a budget
  (`1.5*nvars + 200`), learned clauses with LBD (literal-block distance) > 2 are
  sorted by (LBD, recency) and the worst half removed; clauses that are
  currently the reason for a trail assignment are locked (never deleted) so
  conflict analysis stays valid.

## Per-instance measured times (python3, wall-clock, this machine)

| instance  | verdict | time (s) |
|-----------|---------|----------|
| php7      | UNSAT   | 0.25     |
| php8      | UNSAT   | 1.76     |
| rand150   | SAT     | 0.18     |
| rand200   | SAT     | 1.08     |
| rand250   | SAT     | 2.99     |
| coloring12| SAT     | 0.03     |
| php9      | UNSAT   | 28.3     |
| rand220   | SAT     | 5.68     |
| coloring14| SAT     | 0.03     |

All instances solve well within the 60 s per-instance budget. The pigeonhole
instances (php7/8/9) are the classic DPLL killer; clause learning + restarts are
what make them tractable. php9 (9 pigeons / 8 holes) is by far the hardest and
still finishes ~2x under budget.

## Part B — graph coloring encoding

`encode_coloring.py` reads `coloring12.json` and emits `coloring.cnf` using
variable `v*k + c + 1` = "node v has color c":

- at-least-one-color per node: `n` clauses of width `k`
- at-most-one-color per node: `n * k*(k-1)/2` binary clauses
- edge constraint: `|edges| * k` binary clauses `(-x_{u,c} \/ -x_{v,c})`

It then solves the CNF with our solver and writes `coloring_solution.json`
(`{"colors": [...]}`), deriving each node's color from the satisfied literal
(no `subprocess`, the solver is imported directly to stay within the
stdlib/no-external-program rules).

## What I tried that did not work / was fixed

- **`0` used as "unassigned" level marker** collided with "assigned at decision
  level 0" (units), so units got re-decided and `assigned` over-counted. Fixed
  by using `-1` for unassigned and `0` for root/unit level.
- **VSIDS heap exhaustion**: bumped activities weren't re-pushed, so unassigned
  variables could drop out of the heap and the solver would wrongly report
  UNSAT. Fixed by re-pushing on every bump and rebuilding the heap from
  unassigned vars when it empties.
- **Backtrack-level bug**: the learned clause's backtrack level originally
  included the asserting (UIP) literal, causing an out-of-range `trail_lim`
  index. Fixed to compute the max level over the non-UIP literals only.
- **Clause-deletion reason corruption**: early `reduce_db` remapped/deleted
  learned clauses that were still the reason for trail assignments, leaving
  `reason[v] = None` and crashing conflict analysis. Fixed by locking reason
  clauses and remapping only surviving clauses.
- **Restart at level 0**: restarting right after a backjump-to-0 tried to index
  an empty `trail_lim`. Fixed by guarding restarts to no-op at decision level 0.
- **Growing vs fixed deletion budget**: letting the learned-clause budget grow
  geometrically accumulated a large clause DB and slowed propagation; the fixed
  budget with frequent small reductions kept the DB compact and was faster for
  the pigeonhole instances.
