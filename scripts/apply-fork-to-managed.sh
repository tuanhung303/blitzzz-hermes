#!/usr/bin/env bash
# Apply the fork-local patch-set (speculative compression + TUI statusline) onto
# the MANAGED runtime (~/.hermes/hermes-agent) after `hermes update`.
#
# Workflow this enables:
#   1. hermes update          # managed checkout -> upstream v2026.8.3 (clean)
#   2. bash <this script>     # applies fork-local commits on top of it
#   3. (script runs uv sync + ui-tui build)   # managed venv + TUI dist ready
#
# Design:
#   - The patch source is THIS repo (blitzzz-hermes): everything NOT on
#     upstream/main (git log upstream/main..HEAD, merge commits excluded) is
#     fork-local by construction — speculative compression, TUI statusline,
#     cleanup. No per-file list to maintain.
#   - Guard: refuses to run unless the managed checkout is at the same
#     upstream base (v2026.8.3) and has a clean tree. A half-updated managed
#     (stale HEAD, dirty UI patches from a previous hand-apply) must be
#     refreshed with `hermes update` first.
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

# ---- patch source: fork-local commits only -----------------------------------
cd "$FORK"
git fetch upstream -q 2>/dev/null || true
BASE_SHA="$(git rev-parse upstream/main 2>/dev/null || git rev-parse origin/main)"
LOCAL_COMMITS="$(git log --oneline --no-merges "$BASE_SHA..HEAD" 2>/dev/null | wc -l | tr -d ' ')"
if [[ "$LOCAL_COMMITS" == "0" ]]; then
  echo "no fork-local commits (upstream/main..HEAD) — nothing to apply" >&2
  exit 0
fi
echo "fork-local commits to apply: $LOCAL_COMMITS (base $BASE_SHA)"

# ---- guard: managed must be at the upstream base with a clean tree ------------
cd "$MANAGED"
MANAGED_HEAD="$(git rev-parse --short HEAD)"
if git merge-base --is-ancestor "$BASE_SHA" HEAD 2>/dev/null; then
  echo "managed HEAD $MANAGED_HEAD already contains the fork base ✓"
else
  echo "managed HEAD $MANAGED_HEAD does NOT contain fork base $BASE_SHA."
  echo "run 'hermes update' first so the managed checkout sits on upstream v2026.8.3." >&2
  exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "managed tree is dirty — stash or discard first (hermes update usually resets it):" >&2
  git status --porcelain | head -5 >&2
  exit 1
fi

# ---- generate + apply patch ---------------------------------------------------
PATCH_FILE="$(mktemp /tmp/fork-to-managed-XXXX.patch)"
trap 'rm -f "$PATCH_FILE"' EXIT
git -C "$FORK" format-patch --no-merges --stdout "$BASE_SHA..HEAD" > "$PATCH_FILE"
echo "patch: $PATCH_FILE ($(wc -l < "$PATCH_FILE" | tr -d ' ') lines)"

if [[ "$MODE" == "--check" ]]; then
  echo "--- would apply (check mode) ---"
  git apply --stat "$PATCH_FILE" | tail -15
  exit 0
fi

echo "--- applying ---"
git apply --3way --whitespace=nowarn "$PATCH_FILE" || {
  echo "git apply failed — resolve manually: cd $MANAGED && git apply --3way $PATCH_FILE" >&2
  exit 2
}
echo "applied ✓ (working-tree changes; commit them or leave dirty as your managed convention)"
git status --porcelain | awk '{print "  "$1" "$2}' | head -15

# ---- refresh managed venv + TUI dist ------------------------------------------
echo "--- uv sync (managed venv) ---"
(cd "$MANAGED" && uv sync 2>&1 | tail -3)
echo "--- ui-tui build (managed dist) ---"
(cd "$MANAGED/ui-tui" && npm run build 2>&1 | tail -2)

cat <<EOF

Done. Managed runtime now carries the fork-local surface:
  managed:  $MANAGED
  version:  $("$MANAGED/venv/bin/hermes" --version 2>/dev/null | head -1 || echo '(re-check)')
Run it with:  $MANAGED/venv/bin/hermes
NOTE: the next \`hermes update\` wipes these patches — re-run this script after.
EOF
