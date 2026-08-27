# EXERCISE — HARD MODE: Build a CDCL SAT Solver From Scratch

Difficulty: **super hard**. You have one shot at a clean, correct, fast implementation.
This is a timed benchmark task. Read this whole file before typing anything.

## The Mission

Implement a **complete SAT solver** (CDCL: conflict-driven clause learning) in
**Python 3, standard library only**. It must solve DIMACS CNF instances
correctly AND fast enough to meet the budget below.

A naive DPLL backtracker **will fail the benchmark** — the pigeonhole instances
are the classical worst case for resolution-free search. Your solver needs real
CDCL machinery.

## Deliverables (all at the ROOT of your run folder)

| File | Content |
|---|---|
| `solver.py` | The SAT solver. CLI contract below. |
| `encode_coloring.py` | Part B: graph coloring → CNF encoder. |
| `coloring_solution.json` | Part B: the solved coloring. |
| `notes.md` | Design decisions, measured per-instance times, honest reflection. |

## Part A — solver.py (70%)

### CLI contract
```
python3 solver.py <path/to/instance.cnf>
```
- **stdout**: either `SAT <lit> <lit> ... <lit>` (a full satisfying assignment,
  one nonzero literal per variable, e.g. `SAT 1 -2 3 -4 5`) or `UNSAT`.
- **exit code**: 0 on success. Non-zero only on hard errors.
- **Wall budget**: ≤ 60 s per instance (grader timeout is 120 s; half credit
  between 60 and 120 s).

### Required algorithm features (grader/design review checks these)
1. DIMACS CNF parser: comments (`c ...`), `p cnf <vars> <clauses>` header,
   clauses that may span multiple lines, literals ≠ 0.
2. **Unit propagation with two-watched literals** (no full clause scans on
   every assignment).
3. **VSIDS** (or a better, well-justified decision heuristic).
4. **Conflict analysis + clause learning** (1-UIP) and non-chronological
   backtracking.
5. **Restarts** (Luby or geometric) and **clause deletion/DB reduction**.
6. The solver must be **generic** — it may not special-case specific input
   files, file names, or clause counts. Hidden instances will be graded.

### Constraints
- stdlib only. **No pip installs, no external solvers, no subprocess calls to
  other programs, no network access.**
- Any satisfying assignment is accepted; the grader re-verifies it against the
  clauses itself.

## Part B — encode_coloring.py (20%)

A graph is provided in `task/grader/instances/coloring12.json`:
`{"n": <nodes>, "k": <colors>, "edges": [[u, v], ...]}` (0-indexed nodes).

1. `encode_coloring.py` reads that JSON and writes a DIMACS CNF
   (`coloring.cnf`) encoding proper k-coloring. (Nodes encoded as:
   variable `v*k + c + 1` means "node v has color c".)
2. Solve `coloring.cnf` with YOUR solver and write the result to
   `coloring_solution.json`: `{"colors": [c0, c1, ..., c_{n-1}]}`.
   The grader checks: every node has a color in `0..k-1`, and every edge
   connects differently-colored nodes.

## Rules of Engagement

- Work **only inside your own run folder**. Do not touch anything outside it
  except reading your task files.
- **Do not modify or add anything inside `task/`** — every file there is
  checksummed. Tampering zeroes the affected score.
- No internet, no other agents, no pre-existing SAT solver source, no copying
  from memory of other sessions' code. Original work, please.
- You MAY create helper files/scripts in your run folder and iterate freely.

## Self-Check Before You Declare Done

- [ ] `python3 solver.py task/grader/instances/php7.cnf` → `UNSAT` in ≤ 60 s
- [ ] `python3 solver.py task/grader/instances/rand250.cnf` → `SAT ...` in ≤ 60 s
      (grader will verify the assignment)
- [ ] ALL six visible instances solve within budget (try them all yourself,
      time them, put the numbers in notes.md)
- [ ] `python3 task/grader/grader.py .` prints a scorecard with Part A ≥ 60/70
- [ ] Part B: `python3 encode_coloring.py` + `coloring_solution.json` exist and
      the grader reports Part B = 20/20
- [ ] `task/` is untouched (same files, same content)
- [ ] `notes.md` contains: architecture, each instance's measured time,
      what you tried that didn't work

## How You Will Be Scored

| Section | Weight | Criteria |
|---|---|---|
| Part A visible (6 instances) | 60 | verdict correct + assignment valid + within time budget |
| Part A hidden (3 instances) | 10 | same, instances you never saw |
| Part B coloring | 20 | valid encoding + valid solution |
| notes.md + code clarity | 10 | honest timing table, readable structure, justified design |

Good luck. This is meant to be hard — pigeonhole instances eat naive solvers alive.
