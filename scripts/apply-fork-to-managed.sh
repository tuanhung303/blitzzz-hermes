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
#   - The active surface is the compatibility-checked snapshot under `patches/`.
#     It is generated from the managed tree after speculative removal, so it
#     preserves the remaining compression/memory/statusline/TPS/session-id
#     changes without replaying stale historical commits.
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

ACTIVE_PATCHES=("$FORK"/patches/managed-current-no-spec-*.patch)
if [[ ! -e "${ACTIVE_PATCHES[0]}" ]]; then
  echo "no active consolidated patch found under $FORK/patches" >&2
  exit 1
fi

if [[ "$MODE" == "--check" ]]; then
  echo "--- active non-spec fork patch (check mode) ---"
  for DELTA in "${ACTIVE_PATCHES[@]}"; do
    if git apply --check --whitespace=nowarn "$DELTA" 2>/dev/null; then
      echo "would apply: $(basename "$DELTA")"
    else
      echo "would skip: $(basename "$DELTA") (upstream drift / already applied)"
    fi
  done
  exit 0
fi

# This consolidated patch is generated from the managed tree after the
# speculative layer was removed. It carries the remaining compression/memory,
# statusline, TPS, and session-id deltas without replaying historical commits.
for DELTA in "${ACTIVE_PATCHES[@]}"
do
  [[ -e "$DELTA" ]] || continue
  if git apply --check --whitespace=nowarn "$DELTA" 2>/dev/null; then
    git apply --whitespace=nowarn "$DELTA"
    echo "applied delta: $(basename "$DELTA") ✓"
  else
    echo "delta $(basename "$DELTA") skipped (upstream drift / already applied)"
  fi
done

# Guard: the TUI exit-session-id wiring must be live after its compatible delta;
# if upstream drift skips it, warn instead of claiming that Ctrl+C is resumable.
if ! grep -q "rememberExitSessionId" ui-tui/src/app/useMainApp.ts; then
  echo "WARN: ui-tui/src/app/useMainApp.ts has no rememberExitSessionId wiring —" >&2
  echo "      its compatibility delta did not match this upstream revision;" >&2
  echo "      port patches/tui-exit-session-fix-2026-08.patch" >&2
  echo "      before relying on the Ctrl+C resume line." >&2
fi
git status --porcelain | awk '{print "  "$1" "$2}' | head -15

# ---- refresh managed venv + TUI dist ------------------------------------------
echo "--- uv sync (managed venv) ---"
(cd "$MANAGED" && uv sync 2>&1 | tail -3)
echo "--- ui-tui build (managed dist) ---"
(cd "$MANAGED/ui-tui" && npm run build 2>&1 | tail -2)

cat <<EOF

Done. Managed runtime carries the active non-spec fork surface:
  managed:  $MANAGED
  version:  $("$MANAGED/venv/bin/hermes" --version 2>/dev/null | head -1 || echo '(re-check)')
Run it with:  $MANAGED/venv/bin/hermes
# NOTE: the next "hermes update" wipes compatible deltas — re-run this script after.
EOF
