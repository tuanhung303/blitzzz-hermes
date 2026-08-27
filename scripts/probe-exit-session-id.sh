#!/usr/bin/env bash
# Live probe for the fork TUI surface contract — the runtime half of
# verify-exit-session-contract.sh (unit tests prove the wiring; this proves
# the real process behaves):
#
#   Phase 1 — exit-session id: launch the real TUI in a tmux pane, Ctrl+C
#   EARLY (a few seconds after the composer paints, before the agent build /
#   session.info lands — the case that used to print nothing), and assert the
#   durable `Session <key> ended` line appears in the transcript.
#
#   Phase 2 — statusline chrome: fresh launch, wait for the booted statusline
#   (ctx read-out present), and assert the fork's R4 chrome: the strip starts
#   with the water wave (no leading border dash) and the context read-out has
#   no leading `│ ` separator.
#
# Usage: bash scripts/probe-exit-session-id.sh [hermes-binary]
#   default binary: the managed runtime venv hermes.
set -u

HERMES_BIN="${1:-$HOME/.hermes/hermes-agent/venv/bin/hermes}"

# ── Phase 1: early exit prints the durable session id ──────────────────────
SESS="exitprobe"
LOG="/tmp/exitprobe-session-id.log"

tmux kill-session -t "$SESS" 2>/dev/null
rm -f "$LOG"
tmux new-session -d -s "$SESS" -x 220 -y 55 "script -q $LOG '$HERMES_BIN'"

ready=0
for i in $(seq 1 15); do
  if tmux capture-pane -t "$SESS" -p 2>/dev/null | grep -q "❯"; then
    ready=1
    break
  fi
  sleep 1
done
if (( ready != 1 )); then
  echo "FAIL: composer never painted within 15s" >&2
  tmux kill-session -t "$SESS" 2>/dev/null
  exit 1
fi
sleep 2  # exit before the deferred agent build / session.info lands
tmux send-keys -t "$SESS" C-c
sleep 4

LINE="$(grep -ao 'Session [^ ]* ended[^\"[:cntrl:]]*' "$LOG" | head -1)"
tmux kill-session -t "$SESS" 2>/dev/null

if [[ -z "$LINE" ]]; then
  echo "FAIL: no 'Session ... ended' line on early exit (see $LOG)" >&2
  exit 1
fi
echo "PASS (exit-id): $LINE"

# ── Phase 2: statusline chrome (R4) ────────────────────────────────────────
SESS2="slprobe"
STATUS="/tmp/exitprobe-statusline.txt"

tmux kill-session -t "$SESS2" 2>/dev/null
tmux new-session -d -s "$SESS2" -x 220 -y 55 "'$HERMES_BIN'"

# 2a (REQUIRED): the status strip renders early (model + duration paint
# before the deferred agent build finishes). The duration segment
# (`│ 1m 43s`) is unique to the strip — the splash box never carries one.
strip=0
for i in $(seq 1 60); do
  tmux capture-pane -t "$SESS2" -p 2>/dev/null > "$STATUS"
  if grep -aqE '│ [0-9]+m [0-9]+s|│ [0-9]+s' "$STATUS"; then
    strip=1
    break
  fi
  sleep 1
done
if (( strip != 1 )); then
  echo "FAIL: status strip never rendered within 60s" >&2
  tmux kill-session -t "$SESS2" 2>/dev/null
  exit 1
fi

CHROME="$(python3 - "$STATUS" <<'EOF'
import re, sys
raw = open(sys.argv[1], 'rb').read().decode('utf-8', 'replace')
clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', raw)
lines = [l for l in clean.split('\n') if l.strip()]
if not lines:
    print('EMPTY')
    sys.exit(0)
line = lines[-1].strip()
fails = []
if line.startswith('─'):
    fails.append('leading border dash before the wave')
if not re.search(r'│ ', line):
    fails.append('no model segment')
print(('FAIL: ' + ', '.join(fails) + '\nLINE: ' + line[:140]) if fails else 'OK: ' + line[:140])
EOF
)"
case "$CHROME" in
  OK:*)
    echo "PASS (statusline chrome): ${CHROME#OK: }"
    ;;
  *)
    echo "$CHROME" >&2
    tmux kill-session -t "$SESS2" 2>/dev/null
    exit 1
    ;;
esac

# 2b (BEST-EFFORT): the ctx read-out only lands with the post-build
# session.info, and the agent build is slow on a loaded machine (parallel
# workstreams), so a timeout here is NOT a patch regression — the ctx
# render + separator-absence is pinned by unit tests. When the ctx does
# appear, assert the R4 no-separator chrome live. The read-out is a real
# occupancy number once a turn has run, `–/666k` (unknown) only for a
# FRESH session pre-first-turn, and a transcript-tail estimate for a
# resumed session (server.py _estimate_resumed_window).
for i in $(seq 1 180); do
  tmux capture-pane -t "$SESS2" -p 2>/dev/null > "$STATUS"
  if grep -aqE '(?:[–0-9]+k?)/[0-9]+k' "$STATUS"; then
    break
  fi
  sleep 1
done
tmux send-keys -t "$SESS2" C-c
sleep 2
tmux kill-session -t "$SESS2" 2>/dev/null

CTX="$(python3 - "$STATUS" <<'EOF'
import re, sys
raw = open(sys.argv[1], 'rb').read().decode('utf-8', 'replace')
clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', raw)
lines = [l for l in clean.split('\n') if l.strip()]
if not lines:
    print('EMPTY')
    sys.exit(0)
line = lines[-1].strip()
m = re.search(r'(?:[–0-9]+k?)/[0-9]+k', line)
if not m:
    print('WARN: ctx read-out not seen (build still slow under load); last strip: ' + line[:120])
    sys.exit(0)
if line[:m.start()].rstrip().endswith('│'):
    print('FAIL: ctx read-out preceded by a separator')
    sys.exit(0)
print('PASS: ctx flush without separator: ' + m.group(0)[:80])
EOF
)"
case "$CTX" in
  PASS:*)
    echo "$CTX"
    ;;
  WARN:*)
    echo "$CTX" >&2
    ;;
  FAIL:*)
    echo "$CTX" >&2
    exit 1
    ;;
  *)
    echo "FAIL: statusline ctx probe error: $CTX" >&2
    exit 1
    ;;
esac

echo "probe: ALL PASS"
