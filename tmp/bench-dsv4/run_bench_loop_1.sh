#!/bin/bash
RUN_DIR="/Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/bench-dsv4/runs/ge_med_opt_loop_1"
PROMPT_FILE="/Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/bench-dsv4/results/task_ge_nocompass.txt"
OUT_LOG="$RUN_DIR/agent.log"
TIMING_FILE="$RUN_DIR/timing.json"

cd "$RUN_DIR" || exit 1
echo "=== Starting benchmark ge_med_opt_loop_1 (effort=medium, model=Gemini 3.7 Flash) ==="
T0=$(python3 -c "import time; print(time.time())")

export AGY_MID_TURN_ADVISOR_ENABLED=1
agy --effort medium -p "$(cat "$PROMPT_FILE")" --print-timeout 25m 2>&1 | tee "$OUT_LOG"
RC=$?

T1=$(python3 -c "import time; print(time.time())")
WALL=$(python3 -c "print(round($T1 - $T0, 2))")

echo "=== Benchmark ge_med_opt_loop_1 finished with RC=$RC in ${WALL}s ==="
python3 -c "import json; json.dump({'name': 'ge_med_opt_loop_1', 'effort': 'medium', 'model': 'Gemini 3.7 Flash (Medium)', 't0': $T0, 't1': $T1, 'wall_s': $WALL, 'rc': $RC}, open('$TIMING_FILE', 'w'), indent=2)"

# Run master grader
echo "=== Running master grader ==="
python3 /Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/bench-dsv4/results/gen/grader_master.py "$RUN_DIR" /Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/bench-dsv4/results/gen/hidden > "$RUN_DIR/grade.json" 2>&1
cat "$RUN_DIR/grade.json"
echo "=== Graded ge_med_opt_loop_1 ==="
