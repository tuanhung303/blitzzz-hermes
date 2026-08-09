#!/usr/bin/env bash
# Regression contract for the exit-session-id patch surface.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
CHECKER="$REPO/scripts/check-patch-surface.py"
VERIFIER="$REPO/scripts/verify-exit-session-contract.sh"
SOURCE="${HERMES_MANAGED:-$HOME/.hermes/hermes-agent}"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/hermes-exit-contract.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

copy_contract_surface() {
  local src="$1"
  local dst="$2"
  local file

  for file in \
    tui_gateway/server.py \
    ui-tui/src/app/useInputHandlers.ts \
    ui-tui/src/app/slash/commands/core.ts \
    ui-tui/src/app/useMainApp.ts \
    ui-tui/src/entry.tsx \
    ui-tui/src/lib/sessionExit.ts \
    ui-tui/src/types.ts \
    ui-tui/src/__tests__/createSlashHandler.test.ts \
    ui-tui/src/__tests__/sessionExit.test.ts \
    ui-tui/src/__tests__/useInputHandlers.test.ts; do
    mkdir -p "$dst/$(dirname "$file")"
    cp "$src/$file" "$dst/$file"
  done
}

expect_rejected() {
  local name="$1"
  local root="$2"
  local expected="$3"
  local output

  if output="$(python3 "$CHECKER" "$root" 2>&1)"; then
    echo "FAIL: checker accepted broken surface: $name" >&2
    exit 1
  fi
  if [[ "$output" != *"$expected"* ]]; then
    echo "FAIL: $name rejected for the wrong reason" >&2
    echo "$output" >&2
    exit 1
  fi
  echo "PASS: detects $name"
}

python3 "$CHECKER" "$SOURCE"
echo "PASS: live source satisfies exit-session contract"

if [[ ! -x "$VERIFIER" ]]; then
  echo "FAIL: executable exit-session verifier is missing" >&2
  exit 1
fi

if ! grep -Fq 'check-patch-surface.py' "$REPO/scripts/apply-fork-to-managed.sh"; then
  echo "FAIL: apply workflow does not invoke the patch contract checker" >&2
  exit 1
fi
if ! grep -Fq 'verify-exit-session-contract.sh' "$REPO/scripts/apply-fork-to-managed.sh"; then
  echo "FAIL: apply workflow does not execute tests, rebuild, and validate dist" >&2
  exit 1
fi
if ! grep -Fq 'validate_candidate_patch' "$REPO/scripts/apply-fork-to-managed.sh"; then
  echo "FAIL: --check mode does not validate the candidate patch contract" >&2
  exit 1
fi
maintenance="${HERMES_MAINTENANCE:-$HOME/.hermes/scripts/hermes-maintenance.sh}"
if [[ -f "$maintenance" ]] && ! grep -Fq 'verify-exit-session-contract.sh' "$maintenance"; then
  echo "FAIL: daily maintenance does not execute the exit-session regression contract" >&2
  exit 1
fi
echo "PASS: apply workflow enforces source and dist contracts"

git clone --quiet --shared "$SOURCE" "$TMP/check-runtime"
ln -s "$SOURCE/node_modules" "$TMP/check-runtime/node_modules"
HERMES_MANAGED="$TMP/check-runtime" bash "$REPO/scripts/apply-fork-to-managed.sh" --check
echo "PASS: --check validates the dependency-ordered patch stack"

active_patches=("$REPO"/patches/managed-current-no-spec-*.patch)
if [[ ${#active_patches[@]} -ne 1 || ! -f "${active_patches[0]}" ]]; then
  echo "FAIL: expected exactly one active consolidated patch" >&2
  exit 1
fi
git clone --quiet --shared "$SOURCE" "$TMP/patched"
git -C "$TMP/patched" apply --whitespace=nowarn "${active_patches[0]}"
python3 "$CHECKER" "$TMP/patched"
echo "PASS: active consolidated patch reproduces the exit-session contract"

copy_contract_surface "$SOURCE" "$TMP/base"

mkdir -p "$TMP/base/ui-tui/dist"
printf '%s\n' 'emit(`Session ${sid} ended \\u2014 resume with: hermes --resume ${sid}`)' >"$TMP/base/ui-tui/dist/entry.js"
python3 "$CHECKER" "$TMP/base" --require-dist >/dev/null
cp -R "$TMP/base" "$TMP/no-dist-hint"
printf '%s\n' 'compiled bundle without a resume hint' >"$TMP/no-dist-hint/ui-tui/dist/entry.js"
if python3 "$CHECKER" "$TMP/no-dist-hint" --require-dist >/dev/null 2>&1; then
  echo "FAIL: checker accepted a compiled bundle without the resume line" >&2
  exit 1
fi
echo "PASS: detects compiled bundle drift"

cp -R "$TMP/base" "$TMP/no-flush-import"
python3 - "$TMP/no-flush-import/ui-tui/src/entry.tsx" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
path.write_text(text.replace("import { flushExitSessionId } from './lib/sessionExit.js'\n", '', 1))
PY
expect_rejected "missing flush import" "$TMP/no-flush-import" "entry.tsx must import flushExitSessionId"

cp -R "$TMP/base" "$TMP/no-remember-import"
python3 - "$TMP/no-remember-import/ui-tui/src/app/useMainApp.ts" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
path.write_text(text.replace("import { durableExitSessionId, rememberExitSessionId } from '../lib/sessionExit.js'\n", '', 1))
PY
expect_rejected "missing durable/remember import" "$TMP/no-remember-import" "useMainApp.ts must import durableExitSessionId and rememberExitSessionId"

cp -R "$TMP/base" "$TMP/no-idle-exit-route"
python3 - "$TMP/no-idle-exit-route/ui-tui/src/app/useInputHandlers.ts" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
path.write_text(text.replace('  return actions.die()\n', '  return actions.sys("exit disconnected")\n', 1))
PY
expect_rejected "missing idle Ctrl+C exit route" "$TMP/no-idle-exit-route" "useInputHandlers.ts must route idle exit to actions.die"

cp -R "$TMP/base" "$TMP/no-quit-route"
python3 - "$TMP/no-quit-route/ui-tui/src/app/slash/commands/core.ts" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
path.write_text(text.replace('      ctx.session.die()\n', '      ctx.transcript.sys("exit disconnected")\n', 1))
PY
expect_rejected "missing /quit exit route" "$TMP/no-quit-route" "core.ts must route /quit to ctx.session.die"

cp -R "$TMP/base" "$TMP/no-flush"
python3 - "$TMP/no-flush/ui-tui/src/entry.tsx" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
path.write_text(text.replace('  flushExitSessionId()\n', '', 1))
PY
expect_rejected "missing process-exit flush" "$TMP/no-flush" "entry.tsx exit handler must flush the session id"

cp -R "$TMP/base" "$TMP/no-clear"
python3 - "$TMP/no-clear/ui-tui/src/lib/sessionExit.ts" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
path.write_text(text.replace('  pendingExitSid = null\n', '', 1))
PY
expect_rejected "pending id not cleared after flush" "$TMP/no-clear" "sessionExit.ts must clear the pending id after flush"

cp -R "$TMP/base" "$TMP/invalid-selector-fallback"
python3 - "$TMP/invalid-selector-fallback/ui-tui/src/lib/sessionExit.ts" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
path.write_text(text.replace('sid || null', "sid ?? 'deadbeef'", 1))
PY
expect_rejected "invalid durable-id selector fallback" "$TMP/invalid-selector-fallback" "sessionExit.ts must suppress missing durable ids"

cp -R "$TMP/base" "$TMP/inverted-selector-test"
python3 - "$TMP/inverted-selector-test/ui-tui/src/__tests__/sessionExit.test.ts" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
path.write_text(text.replace('expect(durableExitSessionId(undefined)).toBeNull()', "expect(durableExitSessionId(undefined)).toBe('deadbeef')", 1))
PY
expect_rejected "inverted missing-id selector assertion" "$TMP/inverted-selector-test" "sessionExit.test.ts must execute the missing durable-id suppression path"

cp -R "$TMP/base" "$TMP/commented-gateway-id"
python3 - "$TMP/commented-gateway-id/tui_gateway/server.py" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
path.write_text(text.replace('        "stored_session_id": session_key or "",\n', '        # "stored_session_id": session_key or "",\n', 1))
PY
expect_rejected "commented-out gateway session id" "$TMP/commented-gateway-id" "gateway _session_info must publish stored_session_id"

cp -R "$TMP/base" "$TMP/inverted-regression"
python3 - "$TMP/inverted-regression/ui-tui/src/__tests__/sessionExit.test.ts" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
path.write_text(text.replace('    expect(emit).toHaveBeenCalledTimes(1)\n', '    expect(emit).toHaveBeenCalledTimes(0)\n', 1))
PY
expect_rejected "inverted regression assertion" "$TMP/inverted-regression" "sessionExit.test.ts must assert exactly one emitted line"

cp -R "$TMP/base" "$TMP/inverted-idle-route-test"
python3 - "$TMP/inverted-idle-route-test/ui-tui/src/__tests__/useInputHandlers.test.ts" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
start = text.index("it('exits in normal terminals',")
tail = text[start:].replace('expect(actions.die).toHaveBeenCalledTimes(1)', 'expect(actions.die).toHaveBeenCalledTimes(0)', 1)
path.write_text(text[:start] + tail)
PY
expect_rejected "inverted idle-route assertion" "$TMP/inverted-idle-route-test" "useInputHandlers.test.ts must assert idle Ctrl+C exits exactly once"

cp -R "$TMP/base" "$TMP/inverted-quit-route-test"
python3 - "$TMP/inverted-quit-route-test/ui-tui/src/__tests__/createSlashHandler.test.ts" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
start = text.index("it('exits locally for /quit',")
tail = text[start:].replace('expect(ctx.session.die).toHaveBeenCalledTimes(1)', 'expect(ctx.session.die).toHaveBeenCalledTimes(0)', 1)
path.write_text(text[:start] + tail)
PY
expect_rejected "inverted /quit-route assertion" "$TMP/inverted-quit-route-test" "createSlashHandler.test.ts must assert /quit exits exactly once"

cp -R "$TMP/base" "$TMP/wrong-id"
python3 - "$TMP/wrong-id/ui-tui/src/app/useMainApp.ts" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
path.write_text(text.replace('durableExitSessionId(ui.info?.stored_session_id)', 'ui.sid', 1))
PY
expect_rejected "gateway-internal id fallback used as primary" "$TMP/wrong-id" "useMainApp.ts must use only stored_session_id"

cp -R "$TMP/base" "$TMP/late-remember"
python3 - "$TMP/late-remember/ui-tui/src/app/useMainApp.ts" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
needle = '    rememberExitSessionId(exitSid)\n'
text = text.replace(needle, '', 1)
text = text.replace('    process.exit(0)\n', '    process.exit(0)\n' + needle, 1)
path.write_text(text)
PY
expect_rejected "remember after process.exit" "$TMP/late-remember" "rememberExitSessionId must run before process.exit"

cp -R "$TMP/base" "$TMP/broken-hint"
python3 - "$TMP/broken-hint/ui-tui/src/lib/sessionExit.ts" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
path.write_text(text.replace('hermes --resume ${sid}', 'hermes --resume BROKEN', 1))
PY
expect_rejected "non-resumable output hint" "$TMP/broken-hint" "sessionExit.ts must print the durable id in the resume command"

echo "session-exit patch contract: PASS"
