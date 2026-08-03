#!/usr/bin/env bash
# Reapply the local UI/statusline patch-set after an upstream reset-style sync.
#
# context: upstream-sync.sh rebases (safe — commits survive), but if you ever
# reset main to upstream and re-apply the personal surface, this script is the
# inventory of what to keep. The TUI statusline work (live usage gauge, TPS
# meter, blood-red water wave, session-count tail) is fork-local; upstream does
# not carry it.
#
# Usage:
#   scripts/reapply-ui-patches.sh           # show inventory + current state
#   scripts/reapply-ui-patches.sh --apply   # cherry-pick the UI commits onto HEAD
#
# The listed commits are the tail of this fork's main. Update the list when a
# new UI commit lands (git log --oneline -- ui-tui/ tui_gateway/ | head).

set -euo pipefail

APPLY="${1:-}"

# Oldest-first. These must be re-applied BEFORE the compression-core fixes
# (speculative soft-claim etc.) if you take the whole stack.
UI_COMMITS=(
  # TUI statusline: live usage gauge (session.info push), status tokens
  # "optimizing ctx" (retired), TPS meter, blood-red water wave
  # (exact SHAs change; keep the topic markers below instead)
)

# Instead of hardcoding SHAs (they change on rebase), preserve by topic:
#   git log --oneline --grep="statusline\|tps\|water\|optimizing ctx\|usage gauge" HEAD
#
# When upstream rewrites history under you, rebase once first; if that is
# impossible (upstream force-push / reset), regenerate the patch-set BEFORE
# resetting:
#   git format-patch --stdout $(git merge-base HEAD upstream/main)..HEAD \
#     -- ui-tui/ tui_gateway/ > /tmp/ui-patches.patch
# then after reset:  git apply /tmp/ui-patches.patch

if [[ "$APPLY" == "--apply" ]]; then
  echo "refusing: no hardcoded SHA list; see header for the format-patch flow." >&2
  exit 1
fi

echo "=== UI patch-set inventory (fork-local surface) ==="
echo
echo "Backend (tui_gateway/server.py + tests):"
git log --oneline HEAD --grep="gauge\|statusline\|status update\|session.info" -i | head -6 || true
echo
echo "Frontend (ui-tui/src):"
git log --oneline HEAD --grep="tps\|water\|optimizing ctx\|statusline\|mid-turn\|submit order" -i | head -10 || true
echo
echo "Non-UI compression-core fixes (do NOT drop these either):"
git log --oneline HEAD --grep="speculative\|soft_ready\|soft pressure\|_sessions_lock" -i | head -8 || true
echo
echo "Rebase-based sync (upstream-sync.sh) keeps all of the above automatically."
