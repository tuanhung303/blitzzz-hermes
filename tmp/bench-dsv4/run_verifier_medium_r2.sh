#!/bin/bash
RUN_DIR="/Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/bench-dsv4/runs/ge_med_verifier_r2"
PROMPT_FILE="/Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/bench-dsv4/results/task_ge_nocompass.txt"
OUT_LOG="$RUN_DIR/agent.log"
TIMING_FILE="$RUN_DIR/timing.json"

cd "$RUN_DIR" || exit 1
echo "=== Starting benchmark ge-med-verifier-r2 (effort=medium, verifier=1) ==="
T0=$(python3 -c "import time; print(time.time())")

export AGY_MID_TURN_VERIFIER_ENABLED=1
agy --effort medium -p "$(cat "$PROMPT_FILE")" --print-timeout 25m > "$OUT_LOG" 2>&1
RC=$?

T1=$(python3 -c "import time; print(time.time())")
WALL=$(python3 -c "print(round($T1 - $T0, 2))")

echo "=== Benchmark ge-med-verifier-r2 finished with RC=$RC in ${WALL}s ==="
python3 -c "import json; json.dump({'name': 'ge-med-verifier-r2', 'effort': 'medium', 'mid_verifier': 1, 't0': $T0, 't1': $T1, 'wall_s': $WALL, 'rc': $RC}, open('$TIMING_FILE', 'w'), indent=2)"

# Run master grader
python3 /Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/bench-dsv4/results/gen/grader_master.py "$RUN_DIR" /Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/bench-dsv4/results/gen/task/grader/hidden > "$RUN_DIR/grade.json" 2>&1
echo "=== Graded ge-med-verifier-r2 ==="
cat "$RUN_DIR/grade.json"
