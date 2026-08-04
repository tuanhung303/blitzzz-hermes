#!/usr/bin/env bash
# Reapply the fork-local patch-set (speculative compression + TUI statusline)
# after a clean reset to upstream, or as a sanity inventory after any sync.
#
# context:
#   - `hermes update` only touches the MANAGED runtime (~/.hermes/hermes-agent).
#     It never touches this repo (blitzzz-hermes), so the local surface below
#     survives updates untouched. Nothing to do for the normal update path.
#   - If this repo is ever reset to a bare upstream (upstream-sync.sh rebase is
#     SAFE and keeps all commits — only a manual reset loses them), the fast
#     restore is:  git fetch origin && git reset --hard origin/main
#     because origin/main already contains speculative + UI work.
#   - `--apply` is the manual path for attaching the stack onto an arbitrary
#     base (e.g. a fresh upstream main without the fork history). It
#     cherry-picks the newest commit of each topic that is not already in HEAD.
#
# Topics (oldest-first) cherry-picked by --apply:
#   speculative tool-wait preparation  (feat(compression): speculative tool-wait)
#   speculative lifecycle statusline   (fix(compression): surface speculative | promote speculative)
#   post-tool soft claim               (allow_soft_ready | soft pressure)
#   TUI statusline (gauge/TPS/water)   (statusline | tps | water | usage gauge | Pi statusline)
#   mid-turn submit ordering
#   banner configurability             (startup banner)
#   re-engineering cleanup
#
# AFTER cherry-pick:  uv sync && (cd ui-tui && npm run build) && restart TUI.

set -euo pipefail

MODE="${1:-inventory}"

# ----------------------------- inventory mode --------------------------------
if [[ "$MODE" != "--apply" ]]; then
  echo "=== Fork-local patch inventory (on HEAD) ==="
  for topic in \
    "speculative tool-wait compression" \
    "speculative lifecycle statusline" \
    "allow_soft_ready|soft pressure" \
    "tps|water wave|usage gauge|statusline token" \
    "startup banner" \
    "mid-turn"; do
    echo "  [$topic]"
    git log --oneline HEAD --grep="$topic" -i | head -3
  done
  echo
  echo "Fast restore from origin:  git fetch origin && git reset --hard origin/main"
  echo "Manual re-apply:           $0 --apply"
  exit 0
fi

# ------------------------------ apply mode ------------------------------------
# Find the NEWEST commit matching each topic; cherry-pick only if the change is
# not already present (by grep on the full history below HEAD).
pick_topic() {
  local pattern="$1"
  local sha
  sha=$(git log --oneline --grep="$pattern" -i -1 --format='%H')
  if [[ -z "$sha" ]]; then
    echo "  skip [$pattern]: no matching commit found"
    return 0
  fi
  local subject
  subject=$(git log -1 --format='%s' "$sha")
  if git log HEAD --format='%s' | grep -qiF "${subject%%:*}" 2>/dev/null; then
    echo "  skip [$pattern]: already in HEAD ('${subject%%:*...}')"
    return 0
  fi
  echo "  cherry-pick $sha ($subject)"
  git cherry-pick --no-commit "$sha"
}

echo "=== Applying fork-local patches (in topic order) ==="
pick_topic "feat(compression): speculative tool-wait"
pick_topic "fix(compression): promote speculative"
pick_topic "allow_soft_ready"
pick_topic "usage gauge"
pick_topic "statusline token estimate"
pick_topic "tps meter|midTurnSubmitOrder|water wave"
pick_topic "startup banner"
pick_topic "drop speculative surface"

cat <<'EOF'

Applied as staged changes (no commits made). Next:
  1. resolve any conflicts, then  git commit
  2. uv sync
  3. (cd ui-tui && npm run build)
  4. restart TUI
EOF
