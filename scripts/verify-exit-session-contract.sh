#!/usr/bin/env bash
# Executable exit-session contract: source wiring, route regressions, fresh build, and dist.
set -euo pipefail

ROOT="${1:?usage: verify-exit-session-contract.sh <hermes-runtime-root>}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CHECKER="$REPO/scripts/check-patch-surface.py"

python3 "$CHECKER" "$ROOT"
(
  cd "$ROOT/ui-tui"
  npm test -- --run src/__tests__/sessionExit.test.ts
  npm test -- --run src/__tests__/useInputHandlers.test.ts -t handleIdleHotkeyExit
  npm test -- --run src/__tests__/createSlashHandler.test.ts -t 'exits locally for /quit'
  npm run build
)
python3 "$CHECKER" "$ROOT" --require-dist

echo "exit-session executable contract: PASS"
