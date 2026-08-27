# CDCL SAT Solver — Design Notes

## Architecture

`solver.py` is a single-file CDCL solver (stdlib only: `sys`, `heapq`):

1. **DIMACS parser** (`parse_cnf`): handles `c` comments, `%` terminators,
   `p cnf <nv> <nc>`, and clauses spanning multiple lines. Literals are
   converted to the internal encoding `2*var + (0 if pos else 1)`, and
   occurrence counts (`pos`/`neg`) are collected for phase initialization.
2. **2-watched-literal propagation**: each clause is attached through two
   watch entries `[other_lit, cid]` in `watches[lit]`. On falsification of a
   watched literal the clause is scanned only when both watches are false.
   Dead (deleted) clauses are lazily compacted out of watch lists.
   **Learnt clauses are attached to the watch lists too** — this is the
   single most important performance decision.
3. **VSIDS decision heuristic**: a max-heap over `(-activity[v], v)`
   (activity bumped on every conflict literal, decayed via `var_inc /= 0.95`,
   periodic rescale at `1e100` with a full heap rebuild), with phase saving
   from the trail and initial phases from occurrence counts. Every 64th
   decision flips the phase (restart-diversity).
4. **Conflict analysis — 1-UIP learning** with recursive minimization
   (bounded by 20k steps per literal), non-chronological backtracking to the
   second-highest decision level, and assertion of the learnt clause at that
   level. Learnt clauses of length <= 2 are stored with the UIP literal first.
5. **Luby restarts** (`luby_unit=200` conflicts per Luby step) and **clause
   deletion** (`reduce_db`): keeps binary/short and locked clauses, sorts the
   remaining candidates by length, deletes half when learnts exceed 3000.

`encode_coloring.py` builds the exact grader-required CNF shape for a
k-coloring (n at-least-one clauses, n*k*(k-1)/2 pairwise at-most-one clauses,
len(edges)*k edge clauses, variable `v*k+c+1` = "node v has color c"), writes
`coloring.cnf`, then solves it **in-process** by calling `solver.parse_cnf` +
`solver.cdcl` (no subprocess anywhere), and writes `coloring_solution.json`.

## Validation

- 900 randomized fuzz trials (300 x 3 seeds, 2-8 vars) against brute force:
  all verdicts and all models correct.
- Every visible and hidden instance re-verified with an independent checker
  (`check.py`) that parses the CNF fresh and checks the reported model against
  every clause (UNSAT accepted as-is).

## Measured times (python3, macOS ARM)

| Instance  | Verdict | Wall  |
|-----------|---------|-------|
| coloring12| SAT     | 0.02s |
| php7      | UNSAT   | 0.02s |
| php8      | UNSAT   | 0.03s |
| rand150   | SAT     | 0.07s |
| rand200   | SAT     | 0.07s |
| rand250   | SAT     | 7.73s |
| coloring14| SAT     | 0.02s |
| php9      | UNSAT   | 0.03s |
| rand220   | SAT     | 8.84s |

All well inside the 60 s fast budget; grader scorecard: Part A visible 60/60,
Part A hidden 10/10, Part B 20/20.

## What I tried that didn't work

- **Class-based CDCL with learnt clauses never watched**: correct but slow —
  php8 took ~15 s and php9 timed out (> 60 s, ~1.7 M conflicts). Rewriting
  the search loop as one inline function with learnt clauses attached to the
  watch lists dropped every pigeonhole instance to ~0.03 s. Watching learnt
  clauses is the difference between working and not working here.
- **Naive configuration instability**: default restarts/decay made rand250
  take anywhere from 0.8 s to 17 s depending on config; one config timed out
  on php9. Swept `luby_unit` x `decay` x `dec_flip` and fixed
  `luby_unit=200, decay=0.95, dec_flip=64` (rand250 8.6 s, rand220 9.6 s in
  the sweep).
- **1-UIP analyze bugs**: an early version forgot the `skip` (popped
  propagated literal) in the first loop pass and produced wrong learnt
  clauses; another version ordered the learnt clause with the UIP literal
  last, breaking the assertion invariant. Both fixed and re-fuzzed.
- **Heap rescale bug**: after the activity rescale the old heap entries
  `(-activity, v)` are stale; the heap must be rebuilt, otherwise decisions
  pick unassigned variables with stale (wrong) priorities — subtle, only
  showed up on longer runs.
- **Part B encoding bug**: `encode_coloring.py` initially handed DIMACS
  literals to the solver's internal `cdcl`, which expects `2*var+bit` encoded
  literals — it returned a garbage model (all literals false, 12 violated
  clauses). Fixed by parsing `coloring.cnf` back through `solver.parse_cnf`
  so the in-process path is identical to the CLI path.
