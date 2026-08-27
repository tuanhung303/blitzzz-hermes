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
  # Statusline surface (fork chrome): segment budget, wave, TPS, and the R4
  # regressions (no leading border dash, ctx without separator).
  npm test -- --run src/__tests__/statusRule.test.ts src/__tests__/appChromeStatusRule.test.tsx src/__tests__/tps.test.ts src/__tests__/waterPulse.test.ts
  npm run build
)
python3 "$CHECKER" "$ROOT" --require-dist

echo "exit-session executable contract: PASS"
echo "--- live probe (exit-session id + statusline chrome) ---"
REPO_BIN="$ROOT/venv/bin/hermes"
if [[ -x "$REPO_BIN" ]]; then
  bash "$REPO/scripts/probe-exit-session-id.sh" "$REPO_BIN"
else
  echo "(skip live probe: no managed venv at $REPO_BIN)"
fi
