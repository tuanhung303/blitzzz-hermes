# DeepSeek Model Benchmark: Reasoning Effort vs Quality vs Cost

**Date:** 2026-08-13 · **Harness:** 3 isolated Codex CLI panes (cds wrapper → stock codex, `-p deepseek` profile)
**Task:** super-hard exercise — build a complete CDCL SAT solver from scratch in Python 3 (stdlib only): DIMACS parser, 2-watched-literal propagation, VSIDS, 1-UIP clause learning, Luby restarts, clause deletion, plus a graph-k-coloring → CNF encoder (Part B). 9 graded instances (6 visible + 3 hidden: php7/8/9 pigeonhole, rand150/200/220/250 planted 3-SAT, coloring12/14).

## Results

| | **fl** | **pr** | **pl** |
|---|---|---|---|
| Model + effort | deepseek-v4-flash @ **ultra** (max) | deepseek-v4-pro @ **medium** (standard) | deepseek-v4-pro @ **low** |
| Wall time | 64.5 min | **35.5 min** | 33 min, **aborted — incomplete** |
| Score | **100/100** | **100/100** | **68.3/100** (incomplete) |
| — Part A visible (60) | 60 | 60 | 60 |
| — Part A hidden (10) | 10 | 10 | 8.3 (rand220 over budget) |
| — Part B (20) | 20 | 20 | 0 (not started) |
| — notes (10) | 10 | 10 | 0 (not written) |
| Task integrity | clean | clean | 1 accidental violation (`__pycache__` pyc written inside `task/` by running the grader — Python side-effect, not tampering) |
| Cost (USD) | $0.179 | $0.231 | $0.129 (partial — session killed early) |
| Tokens in (cached) | 21.25M (99.1%) | 9.24M (99.6%) | 4.43M (99.5%) |
| Tokens out (+reasoning) | 336.6K | 207.9K | 117.9K |

## Per-instance solve times (final solver, master-graded)

| Instance | fl (flash@ultra) | pr (pro@medium) | pl (pro@low) |
|---|---|---|---|
| php7 (UNSAT) | 0.04 s | 0.3 s | 0.1 s |
| php8 (UNSAT) | 0.03 s | 2.0 s | 0.8 s |
| php9 (UNSAT, hidden) | **0.04 s** | 29.0 s | 4.6 s |
| rand150 (SAT) | 0.1 s | 0.2 s | 0.1 s |
| rand200 (SAT) | 0.1 s | 1.3 s | 1.8 s |
| rand220 (SAT, hidden) | 9.0 s | **5.5 s** | **106.7 s ✗ over 60 s budget** |
| rand250 (SAT) | 7.6 s | **3.1 s** | 6.7 s |
| coloring12 / coloring14 | 0.0 s / 0.0 s | 0.0 s / 0.0 s | 0.0 s / 0.0 s |

## Verdict

| Dimension | Winner | Margin |
|---|---|---|
| Task completion speed | **pr (pro@medium)** | 35.5 min vs 64.5 min (fl) — pl never finished |
| Quality | **Tie: fl = pr (100/100)**, pl fails | pl's rand220 is 12–19× slower than the others and it ran out of time |
| Cost | fl: $0.179 vs pr: $0.231 | both negligible; DeepSeek context caching (99%+) keeps agent sessions ultra-cheap |
| Final-solver speed | fl wins pigeonhole (php9 0.04 s vs 29 s), pr wins random 3-SAT | interesting split, both far under budget |

**Conclusions**
1. **pro@medium is the best all-rounder**: finished the whole super-hard task in 35.5 min (half fl's time) at a trivial +$0.05, with a 100/100 score. Best quality-per-minute.
2. **flash@ultra is the budget-maximizing alternative**: same 100/100 quality, cheapest, and its final solver even cracked php9 in 0.04 s (an unusually lucky/fast heuristic config). Cost: 64.5 min — double the wall time.
3. **pro@low FAILS**: the reasoning cut degrades solver quality (rand220 over the 60 s budget by ~2×, still iterating at 33 min when it was aborted) while saving almost nothing ($0.13 vs $0.18). Unstable — **not recommended**.

**Recommendation:** daily driver = **deepseek-v4-pro @ medium**; when you want max reasoning depth for hard diagnosis and don't care about wall time = **deepseek-v4-flash @ ultra (max)**. Drop pro@low.

## Caveats
- n=1 per configuration, one task (SAT solver) — noise is real, but the quality gap on pl is large enough to be decisive.
- Agents could see the `hidden/` folder in their task copy; anti-cheat scans (hidden-instance name grep in solver.py + code review) were clean for all three.
- Pricing uses the official DeepSeek API page (flash: $0.14/M in, $0.28/M out; pro: $0.435/M in, $0.87/M out), cache-hit input at $0.0028/$0.003625. Reasoning tokens billed as output.
- `deepseek-v4-max` does not exist on the API (only flash + pro); the "max" candidate was mapped to flash @ ultra effort per the user's matrix choice.
- Codex TUI "─ Worked for Xm ─" separator broke the swarm DONE-parser on all three waves (markers confirmed via pane transcript instead); lesson patched into the swarm skill.
