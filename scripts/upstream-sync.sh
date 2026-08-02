#!/usr/bin/env bash
# upstream-sync.sh — sync the blitzzz-hermes fork with NousResearch/hermes-agent
# while preserving per-feature commits and local customizations.
#
# Pipeline: snapshot branch → stash WIP → fetch upstream → rebase → sanity →
# push origin (--force-with-lease) → restore WIP → reinstall deps (hermes update).
# Stops on conflicts — no auto-resolution (user policy); resolve manually, then
# `git rebase --continue`.
#
# Usage: scripts/upstream-sync.sh                  # full sync + reinstall
#        SKIP_INSTALL=1 scripts/upstream-sync.sh   # sync only
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

UPSTREAM="${UPSTREAM:-upstream}"
BRANCH="$(git branch --show-current)"
if [[ "$BRANCH" != "main" ]]; then
  echo "× script expects branch 'main' (got '$BRANCH') — aborting" >&2
  exit 1
fi

VENV_PY="${VENV_PY:-$HOME/.hermes/hermes-agent/venv/bin/python}"
if [[ ! -x "$VENV_PY" ]]; then
  echo "× venv python not found at $VENV_PY (set VENV_PY)" >&2
  exit 1
fi

echo "== 1/8 snapshot + stash =="
SNAP="backup/pre-rebase-$(date -u +%Y%m%dT%H%M%SZ)"
if git branch "$SNAP" 2>/dev/null; then
  echo "   snapshot: $SNAP"
else
  echo "   snapshot exists: $SNAP"
fi

STASHED=0
if [[ -n "$(git status --porcelain)" ]]; then
  git stash push -u -m "upstream-sync: WIP before rebase $(date -u +%Y%m%dT%H%M%SZ)"
  STASHED=1
  echo "   WIP stashed ($(git stash list -1 --format=%gd))"
fi

echo "== 2/8 fetch $UPSTREAM =="
git fetch "$UPSTREAM"
if ! git rev-parse --verify -q "refs/remotes/$UPSTREAM/main" >/dev/null; then
  echo "× no $UPSTREAM/main — add the remote first:" >&2
  echo "    git remote add upstream https://github.com/NousResearch/hermes-agent.git" >&2
  if [[ "$STASHED" -eq 1 ]]; then git stash pop; fi
  exit 1
fi

echo "== 3/8 drift =="
DRIFT="$(git rev-list --left-right --count "$UPSTREAM/main"...HEAD)"
BEHIND="${DRIFT%%$'\t'*}"
AHEAD="${DRIFT##*$'\t'}"
echo "   behind: $BEHIND | ahead: $AHEAD"
if [[ "$AHEAD" -eq 0 ]]; then
  echo "   nothing to rebase — already in sync"
  if [[ "$STASHED" -eq 1 ]]; then git stash pop; fi
  exit 0
fi

echo "== 4/8 rebase onto $UPSTREAM/main =="
if ! git rebase "$UPSTREAM/main"; then
  echo ""
  echo "×× CONFLICTS — stopped on purpose (no auto-resolution)."
  echo "   Resolve manually, then continue:"
  echo "     git add <resolved files> && git rebase --continue"
  echo "   or abort everything:"
  echo "     git rebase --abort && git stash pop"
  exit 1
fi

echo "== 5/8 sanity =="
SCAN_EMOJI="$HOME/.hermes/skills/devops/hermes-cli-customization/scripts/scan_emoji.py"
if [[ -f "$SCAN_EMOJI" ]]; then
  "$VENV_PY" "$SCAN_EMOJI" || echo "⚠ emoji scan reports issues — inspect before pushing"
fi
"$VENV_PY" -m pytest \
  tests/hermes_cli/test_config_validation.py \
  tests/hermes_cli/test_config.py \
  tests/cli/test_cli_status_bar.py \
  -q -o 'addopts=' || { echo "× tests failed — do NOT push. Fix, then re-run." >&2; exit 1; }

echo "== 6/8 push origin main (--force-with-lease) =="
git push origin main --force-with-lease

echo "== 7/8 restore WIP =="
if [[ "$STASHED" -eq 1 ]]; then
  git stash pop || echo "⚠ stash pop conflicted — resolve manually, then: git stash drop"
fi

echo "== 8/8 install (deps reinstall + import validation) =="
if [[ "${SKIP_INSTALL:-0}" != "1" ]]; then
  hermes update || echo "⚠ 'hermes update' reported problems — run 'hermes doctor'"
else
  echo "   skipped (SKIP_INSTALL=1)"
fi

echo "✓ sync complete — restart the TUI for the new build"
