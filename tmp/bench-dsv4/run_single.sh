#!/bin/bash
RUN_DIR="$1"
EFFORT="$2"
NAME="$3"
PROMPT_FILE="/Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/bench-dsv4/results/task_ge_nocompass.txt"
OUT_LOG="$RUN_DIR/agent.log"
TIMING_FILE="$RUN_DIR/timing.json"

cd "$RUN_DIR" || exit 1
echo "=== Starting benchmark $NAME (effort=$EFFORT) in $RUN_DIR ==="
T0=$(python3 -c "import time; print(time.time())")

agy --effort "$EFFORT" -p "$(cat "$PROMPT_FILE")" --print-timeout 25m > "$OUT_LOG" 2>&1
RC=$?

T1=$(python3 -c "import time; print(time.time())")
WALL=$(python3 -c "print(round($T1 - $T0, 2))")

echo "=== Benchmark $NAME finished with RC=$RC in ${WALL}s ==="
python3 -c "import json; json.dump({'name': '$NAME', 'effort': '$EFFORT', 't0': $T0, 't1': $T1, 'wall_s': $WALL, 'rc': $RC}, open('$TIMING_FILE', 'w'), indent=2)"

# Run master grader
python3 /Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/bench-dsv4/results/gen/grader_master.py "$RUN_DIR" /Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/bench-dsv4/results/gen/task/grader/hidden > "$RUN_DIR/grade.json" 2>&1
echo "=== Graded $NAME ==="
cat "$RUN_DIR/grade.json"
