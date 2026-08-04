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
# This repo is a patch-set repo now: commit history lives on the
# full-fork-v202683 backup branch. That branch is the tip of the merged
# main, whose history contains BOTH pre-rebase and rebased copies of each
# change. Resolve the source to the rebased-only chain: the second parent
# of the 'Merge branch sync-v202683' commit. Verified 35 commits, 0 dupes.
PATCH_SOURCE_REF="full-fork-v202683"
SYNC_MERGE="$(git log --format='%H %s' --merges full-fork-v202683 \
  | grep 'Merge branch .sync-v202683' | awk '{print $1}' | head -1)"
if [[ -n "$SYNC_MERGE" && -n "$(git rev-parse -q --verify "${SYNC_MERGE}^2")" ]]; then
  PATCH_SOURCE_REF="${SYNC_MERGE}^2"
fi
LOCAL_COMMITS="$(git log --oneline --no-merges "$BASE_SHA..$PATCH_SOURCE_REF" 2>/dev/null | wc -l | tr -d ' ')"
if [[ "$LOCAL_COMMITS" == "0" ]]; then
  echo "no fork-local commits ($BASE_SHA..$PATCH_SOURCE_REF) — nothing to apply" >&2
  exit 0
fi
echo "fork-local commits to apply: $LOCAL_COMMITS from $PATCH_SOURCE_REF (base $BASE_SHA)"

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
git -C "$FORK" format-patch --no-merges --stdout "$BASE_SHA..$PATCH_SOURCE_REF" > "$PATCH_FILE"
echo "patch: $PATCH_FILE ($(wc -l < "$PATCH_FILE" | tr -d ' ') lines)"

if [[ "$MODE" == "--check" ]]; then
  echo "--- would apply (check mode) ---"
  git apply --stat "$PATCH_FILE" | tail -15
  exit 0
fi

echo "--- applying ---"
git apply --whitespace=nowarn "$PATCH_FILE" || {
  echo "git apply failed — resolve manually: cd $MANAGED && git apply --whitespace=nowarn $PATCH_FILE" >&2
  exit 2
}
echo "applied ✓ (working-tree changes; commit them or leave dirty as your managed convention)"

# Optional follow-up deltas applied on top of the main patch (field fixes that
# shipped after the 35-commit snapshot, e.g. statusline-fix-2026-08.patch).
for DELTA in "$FORK"/patches/statusline-fix-*.patch; do
  [[ -e "$DELTA" ]] || continue
  if git apply --check --whitespace=nowarn "$DELTA" 2>/dev/null; then
    git apply --whitespace=nowarn "$DELTA"
    echo "applied delta: $(basename "$DELTA") ✓"
  else
    echo "delta $(basename "$DELTA") skipped (already present / conflicts — likely already applied)"
  fi
done
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
