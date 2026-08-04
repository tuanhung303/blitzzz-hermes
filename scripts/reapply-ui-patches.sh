#!/usr/bin/env bash
# Inventory the active non-spec local patch snapshot after an upstream reset.
# The retired speculative-compression history is not replayed.
#
# context:
#   - `hermes update` only touches the MANAGED runtime (~/.hermes/hermes-agent).
#     It never touches this repo (blitzzz-hermes), so the local surface below
#     survives updates untouched. Nothing to do for the normal update path.
#   - If this repo is ever reset to a bare upstream (upstream-sync.sh rebase is
#     SAFE and keeps all commits — only a manual reset loses them), the fast
#     restore is:  git fetch origin && git reset --hard origin/main
#     because origin/main contains the patch-set metadata and compatibility
#     deltas.
#   - `--apply` is intentionally not a historical cherry-pick path. Apply via
#     scripts/apply-fork-to-managed.sh so the snapshot is compatibility-checked.
#
# Active compatibility snapshot:
#   patches/managed-current-no-spec-20260804.patch
#
# AFTER a compatible delta applies: uv sync && (cd ui-tui && npm run build) && restart TUI.

set -euo pipefail

MODE="${1:-inventory}"

# ----------------------------- inventory mode --------------------------------
if [[ "$MODE" != "--apply" ]]; then
  echo "=== Fork-local patch inventory (on HEAD) ==="
  for topic in \
    "tps|water wave|usage gauge|statusline token" \
    "startup banner|banner/summary panel" \
    "submit order"; do
    echo "  [$topic]"
    git log --oneline --extended-regexp HEAD --grep="$topic" -i | head -3
  done
  echo
  echo "Fast restore from origin:  git fetch origin && git reset --hard origin/main"
  echo "Compatibility apply:        scripts/apply-fork-to-managed.sh"
  exit 0
fi

echo "Historical cherry-picks are disabled: full-fork-v202683 is backup-only."
echo "Use scripts/apply-fork-to-managed.sh to apply compatibility-checked deltas."

cat <<'EOF'

No changes made.
EOF
