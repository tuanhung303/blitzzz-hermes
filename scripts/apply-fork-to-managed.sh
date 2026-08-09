#!/usr/bin/env bash
# Apply the active non-spec fork snapshot onto the MANAGED runtime
# (~/.hermes/hermes-agent) after `hermes update`.
#
# Workflow this enables:
#   1. hermes update          # managed checkout -> upstream v2026.8.3 (clean)
#   2. bash <this script>     # applies the active non-spec snapshot on top of it
#   3. (script runs uv sync + ui-tui build)   # managed venv + TUI dist ready
#
# Design:
#   - `full-fork-v202683` remains an immutable historical backup only. It is
#     never formatted or replayed here: that history contains the retired
#     speculative-compression implementation and its TUI/status hooks.
#   - The active surface is the compatibility-checked snapshot plus focused
#     additive patches under `patches/`. The snapshot is generated from the
#     managed tree after speculative removal; focused patches keep newer fork
#     behavior reviewable without regenerating that large baseline.
#   - Guard: the managed checkout must be clean. A half-updated managed runtime
#     must be refreshed with `hermes update` first.
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
cd "$FORK"
cd "$MANAGED"
MANAGED_HEAD="$(git rev-parse --short HEAD)"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "managed tree is dirty — stash or discard first (hermes update usually resets it):" >&2
  git status --porcelain | head -5 >&2
  exit 1
fi
echo "managed HEAD $MANAGED_HEAD is clean; legacy fork history is inactive"

shopt -s nullglob
BASE_PATCHES=("$FORK"/patches/managed-current-no-spec-*.patch)
RUNTIME_PATCHES=("$FORK"/patches/runtime-budget-*.patch)
shopt -u nullglob
if [[ ${#BASE_PATCHES[@]} -ne 1 || ${#RUNTIME_PATCHES[@]} -ne 1 ]]; then
  echo "expected exactly one consolidated patch and one runtime-budget patch" >&2
  exit 1
fi
ACTIVE_PATCHES=("${BASE_PATCHES[0]}" "${RUNTIME_PATCHES[0]}")

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
    if [[ ! -d "$MANAGED/node_modules" ]]; then
      echo "managed runtime lacks node_modules required for candidate verification" >&2
      exit 1
    fi
    ln -s "$MANAGED/node_modules" "$candidate/node_modules"
    bash "$FORK/scripts/verify-exit-session-contract.sh" "$candidate"
  ); then
    rm -rf "$candidate"
    echo "ERROR: candidate patch stack fails validation" >&2
    return 1
  fi

  rm -rf "$candidate"
  echo "candidate patch stack: OK"
}

if [[ "$MODE" == "--check" ]]; then
  echo "--- active non-spec fork patch (check mode) ---"
  validate_candidate_patch_stack
  exit 0
fi

# This consolidated patch is generated from the managed tree after the
# speculative layer was removed. It carries the remaining compression/memory,
# statusline, TPS, and session-id deltas without replaying historical commits.
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
  echo "No build performed. Port the consolidated patch to this upstream revision first." >&2
  exit 1
fi

REQUIRED_SURFACE=(
  "agent/prompt_builder.py:INTERACTIVE_EXECUTION_BUDGET_GUIDANCE"
  "tools/runtime_budget.py:runtime_advice"
  "ui-tui/src/components/appChrome.tsx:waterFrameStep"
  "tui_gateway/server.py:message.throughput"
)
for CHECK in "${REQUIRED_SURFACE[@]}"; do
  FILE="${CHECK%%:*}"
  MARKER="${CHECK#*:}"
  if ! grep -Fq "$MARKER" "$FILE"; then
    echo "ERROR: patch surface incomplete: $FILE lacks $MARKER" >&2
    exit 1
  fi
done

# A single marker is insufficient: prior snapshots retained the symbol while
# losing another leg of the durable-id → exit-handler → stdout chain. Validate
# the complete source contract and fail before building when any leg drifts.
python3 "$FORK/scripts/check-patch-surface.py" "$MANAGED"
git status --porcelain | awk '{print "  "$1" "$2}' | head -15

# ---- refresh managed venv + TUI dist ------------------------------------------
echo "--- uv sync (managed venv) ---"
(cd "$MANAGED" && uv sync 2>&1 | tail -3)
echo "--- executable exit-session contract ---"
bash "$FORK/scripts/verify-exit-session-contract.sh" "$MANAGED"

cat <<EOF

Done. Managed runtime carries the active non-spec fork surface:
  managed:  $MANAGED
  version:  $("$MANAGED/venv/bin/hermes" --version 2>/dev/null | head -1 || echo '(re-check)')
Run it with:  $MANAGED/venv/bin/hermes
# NOTE: the next "hermes update" wipes compatible deltas — re-run this script after.
EOF
