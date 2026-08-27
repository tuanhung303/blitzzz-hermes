#!/usr/bin/env bash
# Apply the active fork snapshot onto the MANAGED runtime
# (~/.hermes/hermes-agent) after `hermes update`.
#
# Workflow this enables:
#   1. hermes update          # managed checkout -> upstream (clean)
#   2. bash <this script>     # applies the active snapshot on top of it
#   3. (script runs uv sync + TUI check)   # managed venv + TUI ready
#
# Design:
#   - `fork-local-v202683.patch` remains an immutable historical backup only.
#   - The active surface is ONE consolidated snapshot
#     `patches/managed-current-20260814.patch` (regenerated from the managed
#     tree after each update cycle; 2026-08-14 = the v2026.8.13 port that
#     dropped speculative-compression, sessionExit, and re-homed water/TPS on
#     the segment-based StatusRule). Focused per-feature patches from earlier
#     rounds were absorbed into it (patches/absorbed-20260814/).
#   - Guard: the managed checkout must be clean. A half-updated managed
#     runtime must be refreshed with `hermes update` first.
#
# Options:
#   --check     dry run: print what would be applied, change nothing.
#   --help

set -euo pipefail

FORK="$(cd "$(dirname "$0")/.." && pwd)"
MANAGED="${HERMES_MANAGED:-$HOME/.hermes/hermes-agent}"
MODE="${1:-apply}"

if [[ ! -d "$MANAGED/.git" ]]; then
  echo "managed runtime not found at $MANAGED (set HERMES_MANAGED to override)" >&2
  exit 1
fi

# ---- managed guard -------------------------------------------------------------
# Idempotent re-run: a tree whose dirty content is EXACTLY the active snapshot
# (reverse-applies cleanly) is already carrying the surface — not a half-update.
cd "$MANAGED"
MANAGED_HEAD="$(git rev-parse --short HEAD)"
ACTIVE_SNAPSHOT="$(ls "$FORK"/patches/managed-current-*.patch 2>/dev/null | head -1)"
if [[ -n "$(git status --porcelain)" ]]; then
  if [[ -n "$ACTIVE_SNAPSHOT" ]] && git apply --reverse --check --whitespace=nowarn "$ACTIVE_SNAPSHOT" 2>/dev/null; then
    echo "managed HEAD $MANAGED_HEAD already carries the active snapshot — nothing to apply"
    exit 0
  fi
  echo "managed tree is dirty and NOT the active snapshot — stash or discard first:" >&2
  git status --porcelain | head -5 >&2
  exit 1
fi
echo "managed HEAD $MANAGED_HEAD is clean; legacy fork history is inactive"

shopt -s nullglob
BASE_PATCHES=("$FORK"/patches/managed-current-*.patch)
shopt -u nullglob
if [[ ${#BASE_PATCHES[@]} -ne 1 ]]; then
  echo "expected exactly one consolidated snapshot under patches/managed-current-*.patch" >&2
  exit 1
fi
ACTIVE_PATCHES=("${BASE_PATCHES[0]}")

# ---- surface contract ----------------------------------------------------------
# One marker per ported feature, validated on the candidate clone (--check) and
# on the live tree AFTER apply. The consolidated snapshot regenerated from a
# verified tree carries these; a half-ported snapshot fails the gate.
REQUIRED_SURFACE=(
  "ui-tui/src/components/appChrome.tsx:waterFrameStep"
  "ui-tui/src/components/appChrome.tsx:waterCellCount"
  "ui-tui/src/components/appChrome.tsx:TpsMeter"
  "ui-tui/src/components/appChrome.tsx:STATUS_METRIC_GRAY"
  "ui-tui/src/app/tpsStore.ts:feedTpsChars"
  "ui-tui/src/app/wavePulseStore.ts:pulseWave"
  "ui-tui/src/app/createGatewayEventHandler.ts:resetLiveBackgroundProbe"
  "ui-tui/src/app/createGatewayEventHandler.ts:feedTpsChars"
  "ui-tui/src/lib/sessionExit.ts:flushExitSessionId"
  "ui-tui/src/app/useMainApp.ts:rememberExitSessionId"
  "ui-tui/src/app/useMainApp.ts:ui.info?.stored_session_id"
  "ui-tui/src/app/useSessionLifecycle.ts:stored_session_id: r.stored_session_id"
  "ui-tui/src/__tests__/appChromeStatusRule.test.tsx:no leading border dash"
  "ui-tui/src/__tests__/appChromeStatusRule.test.tsx:without a leading separator"
  "ui-tui/src/__tests__/appChromeStatusRule.test.tsx:instead of fabricating 0"
  "ui-tui/src/__tests__/sessionExit.test.ts:rememberExitSessionId"
  "ui-tui/src/entry.tsx:flushExitSessionId"
  "tui_gateway/server.py:context_max is factual"
  "tui_gateway/server.py:_tui_resumed_window_estimate"
  "tools/runtime_budget.py:runtime_advice"
  "agent/prompt_builder.py:INTERACTIVE_EXECUTION_BUDGET_GUIDANCE"
  "tui_gateway/server.py:Never fall back to the lifetime session total"
  "tui_gateway/methods_session.py:estimated_total"
  "hermes_cli/terminal_bg_probe.py:HERMES_TUI_BACKGROUND"
)

validate_candidate_patch_stack() {
  local candidate
  candidate="$(mktemp -d "${TMPDIR:-/tmp}/hermes-patch-contract.XXXXXX")"

  if ! (
    git clone --quiet --shared "$MANAGED" "$candidate"
    for delta in "${ACTIVE_PATCHES[@]}"; do
      if git -C "$candidate" apply --check --whitespace=nowarn "$delta" 2>/dev/null; then
        git -C "$candidate" apply --whitespace=nowarn "$delta"
        echo "would apply: $(basename "$delta")"
      elif git -C "$candidate" apply --reverse --check --whitespace=nowarn "$delta" 2>/dev/null; then
        echo "already applied: $(basename "$delta")"
      else
        echo "incompatible: $(basename "$delta") (upstream drift)" >&2
        exit 1
      fi
    done
    for CHECK in "${REQUIRED_SURFACE[@]}"; do
      FILE="${CHECK%%:*}"
      MARKER="${CHECK#*:}"
      if ! grep -Fq "$MARKER" "$candidate/$FILE"; then
        echo "candidate patch stack lacks $FILE marker $MARKER" >&2
        exit 1
      fi
    done
  ); then
    rm -rf "$candidate"
    echo "ERROR: candidate patch stack fails validation" >&2
    return 1
  fi

  rm -rf "$candidate"
  echo "candidate patch stack: OK"
}

if [[ "$MODE" == "--check" ]]; then
  echo "--- active fork snapshot (check mode) ---"
  validate_candidate_patch_stack
  exit 0
fi

APPLY_FAILED=0
for DELTA in "${ACTIVE_PATCHES[@]}"
do
  [[ -e "$DELTA" ]] || continue
  if git apply --check --whitespace=nowarn "$DELTA" 2>/dev/null; then
    git apply --whitespace=nowarn "$DELTA"
    echo "applied delta: $(basename "$DELTA") ✓"
  elif git apply --reverse --check --whitespace=nowarn "$DELTA" 2>/dev/null; then
    echo "delta already applied: $(basename "$DELTA") ✓"
  else
    echo "ERROR: delta $(basename "$DELTA") is incompatible with managed HEAD $MANAGED_HEAD" >&2
    APPLY_FAILED=1
  fi
done

if (( APPLY_FAILED != 0 )); then
  echo "No build performed. Port the consolidated snapshot to this upstream revision first." >&2
  exit 1
fi

# Re-check markers on the live tree (the candidate clone above may be stale).
for CHECK in "${REQUIRED_SURFACE[@]}"; do
  FILE="${CHECK%%:*}"
  MARKER="${CHECK#*:}"
  if ! grep -Fq "$MARKER" "$FILE"; then
    echo "ERROR: patch surface incomplete after apply: $FILE lacks $MARKER" >&2
    exit 1
  fi
done
git status --porcelain | awk '{print "  "$1" "$2}' | head -15

# ---- refresh managed venv ------------------------------------------------------
echo "--- uv sync (managed venv) ---"
(cd "$MANAGED" && uv sync 2>&1 | tail -3)

cat <<EOF

Done. Managed runtime carries the active fork surface:
  managed:  $MANAGED
  version:  $("$MANAGED/venv/bin/hermes" --version 2>/dev/null | head -1 || echo '(re-check)')
Run it with:  $MANAGED/venv/bin/hermes
# NOTE: the next "hermes update" wipes compatible deltas — re-run this script after.
EOF
