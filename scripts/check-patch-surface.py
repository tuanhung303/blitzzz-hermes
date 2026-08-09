#!/usr/bin/env python3
"""Fail-closed validation for the Hermes fork patch surface."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


class ContractError(RuntimeError):
    """Raised when a required patch contract is absent or misordered."""


def read_required(root: Path, relative: str) -> str:
    path = root / relative
    try:
        return path.read_text()
    except FileNotFoundError as exc:
        raise ContractError(f"missing required patch file: {relative}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def block_between(text: str, start: str, end: str, source: str) -> str:
    start_index = text.find(start)
    require(start_index >= 0, f"{source} lacks {start}")
    end_index = text.find(end, start_index + len(start))
    require(end_index >= 0, f"{source} lacks boundary {end}")
    return text[start_index:end_index]


def gateway_publishes_durable_session_id(source: str) -> bool:
    """Require a live _session_info dictionary entry, not a comment/string marker."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ContractError(f"tui_gateway/server.py is not valid Python: {exc}") from exc

    session_info = next(
        (node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_session_info"),
        None,
    )
    if session_info is None:
        return False

    for node in ast.walk(session_info):
        value: ast.expr | None = None
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            value = node.value
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            value = node.value
            targets = [node.target]
        if not isinstance(value, ast.Dict):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "info" for target in targets):
            continue
        for key, item in zip(value.keys, value.values, strict=False):
            if not (isinstance(key, ast.Constant) and key.value == "stored_session_id"):
                continue
            return (
                isinstance(item, ast.BoolOp)
                and isinstance(item.op, ast.Or)
                and len(item.values) == 2
                and isinstance(item.values[0], ast.Name)
                and item.values[0].id == "session_key"
                and isinstance(item.values[1], ast.Constant)
                and item.values[1].value == ""
            )
    return False


def validate(root: Path, require_dist: bool = False) -> None:
    use_main = read_required(root, "ui-tui/src/app/useMainApp.ts")
    require(
        "import { durableExitSessionId, rememberExitSessionId } from '../lib/sessionExit.js'" in use_main,
        "useMainApp.ts must import durableExitSessionId and rememberExitSessionId",
    )
    die = block_between(
        use_main,
        "const die = useCallback(() => {",
        "const dieWithCode = useCallback(",
        "useMainApp.ts",
    )
    require(
        "durableExitSessionId(ui.info?.stored_session_id)" in die,
        "useMainApp.ts must use only stored_session_id and suppress non-resumable fallback ids",
    )
    remember_index = die.find("rememberExitSessionId(exitSid)")
    process_exit_index = die.find("process.exit(0)")
    require(remember_index >= 0, "useMainApp.ts die() must remember the exit session id")
    require(process_exit_index >= 0, "useMainApp.ts die() lacks process.exit(0)")
    require(
        remember_index < process_exit_index,
        "useMainApp.ts rememberExitSessionId must run before process.exit",
    )

    input_handlers = read_required(root, "ui-tui/src/app/useInputHandlers.ts")
    idle_exit = block_between(
        input_handlers,
        "export function handleIdleHotkeyExit(",
        "/**",
        "useInputHandlers.ts",
    )
    require(
        "return actions.die()" in idle_exit,
        "useInputHandlers.ts must route idle exit to actions.die",
    )
    ctrl_c_route = block_between(
        input_handlers,
        "if (key.ctrl && ch.toLowerCase() === 'c') {",
        "if (isAction(key, ch, 'd')) {",
        "useInputHandlers.ts Ctrl+C route",
    )
    require(
        "return handleIdleHotkeyExit(actions" in ctrl_c_route,
        "useInputHandlers.ts idle Ctrl+C must call handleIdleHotkeyExit",
    )

    core_commands = read_required(root, "ui-tui/src/app/slash/commands/core.ts")
    quit_command = block_between(
        core_commands,
        "name: 'quit',",
        "\n  },\n\n  {",
        "core.ts /quit command",
    )
    require(
        "ctx.session.die()" in quit_command,
        "core.ts must route /quit to ctx.session.die",
    )

    entry = read_required(root, "ui-tui/src/entry.tsx")
    require(
        "import { flushExitSessionId } from './lib/sessionExit.js'" in entry,
        "entry.tsx must import flushExitSessionId",
    )
    exit_handler = block_between(
        entry,
        "process.on('exit', () => {",
        "})",
        "entry.tsx",
    )
    reset_index = exit_handler.find("resetTerminalModes()")
    flush_index = exit_handler.find("flushExitSessionId()")
    require(reset_index >= 0, "entry.tsx exit handler must reset terminal modes")
    require(flush_index >= 0, "entry.tsx exit handler must flush the session id")
    require(
        reset_index < flush_index,
        "entry.tsx must reset terminal modes before flushing the session id",
    )

    session_exit = read_required(root, "ui-tui/src/lib/sessionExit.ts")
    for marker, message in (
        (
            "durableExitSessionId = (sid: null | string | undefined): null | string => sid || null",
            "sessionExit.ts must suppress missing durable ids",
        ),
        ("writeSync(1, text)", "sessionExit.ts must synchronously write to stdout"),
        ("let pendingExitSid: null | string = null", "sessionExit.ts lacks pending exit state"),
        (
            "hermes --resume ${sid}",
            "sessionExit.ts must print the durable id in the resume command",
        ),
    ):
        require(marker in session_exit, message)

    flush_start = session_exit.find("export const flushExitSessionId")
    require(flush_start >= 0, "sessionExit.ts lacks flushExitSessionId")
    emit_index = session_exit.find("emitSessionIdAtExit(pendingExitSid, emit)", flush_start)
    clear_index = session_exit.find("pendingExitSid = null", flush_start)
    require(emit_index >= 0, "sessionExit.ts flush must emit the pending id")
    require(
        clear_index > emit_index,
        "sessionExit.ts must clear the pending id after flush",
    )

    types = read_required(root, "ui-tui/src/types.ts")
    require("stored_session_id?: string" in types, "SessionInfo lacks stored_session_id")

    server = read_required(root, "tui_gateway/server.py")
    require(
        gateway_publishes_durable_session_id(server),
        "gateway _session_info must publish stored_session_id",
    )

    tests = read_required(root, "ui-tui/src/__tests__/sessionExit.test.ts")
    selector_test = block_between(
        tests,
        "it('suppresses missing or empty ids instead of falling back to the gateway sid',",
        "  })",
        "sessionExit.test.ts durable selector regression",
    )
    require(
        "expect(durableExitSessionId(undefined)).toBeNull()" in selector_test
        and "expect(durableExitSessionId('')).toBeNull()" in selector_test,
        "sessionExit.test.ts must execute the missing durable-id suppression path",
    )
    emit_test = block_between(
        tests,
        "it('emits the session id with a resume hint',",
        "  })",
        "sessionExit.test.ts emit regression",
    )
    require(
        "expect(emit).toHaveBeenCalledTimes(1)" in emit_test,
        "sessionExit.test.ts must assert exactly one emitted line",
    )
    require(
        "hermes --resume abc123" in emit_test,
        "sessionExit.test.ts must assert the emitted id in the resume command",
    )
    flush_test = block_between(
        tests,
        "it('regression: flush emits the remembered durable id exactly once, then clears',",
        "  })",
        "sessionExit.test.ts durable-id regression",
    )
    require(
        "expect(emit).toHaveBeenCalledTimes(1)" in flush_test,
        "sessionExit.test.ts must assert exactly one emitted line",
    )
    require(
        "hermes --resume 20260804_113730_2d05f2" in flush_test,
        "sessionExit.test.ts must assert the durable id in the resume command",
    )

    input_tests = read_required(root, "ui-tui/src/__tests__/useInputHandlers.test.ts")
    idle_test = block_between(
        input_tests,
        "it('exits in normal terminals',",
        "  })",
        "useInputHandlers.test.ts idle exit regression",
    )
    require(
        "expect(actions.die).toHaveBeenCalledTimes(1)" in idle_test,
        "useInputHandlers.test.ts must assert idle Ctrl+C exits exactly once",
    )

    slash_tests = read_required(root, "ui-tui/src/__tests__/createSlashHandler.test.ts")
    quit_test = block_between(
        slash_tests,
        "it('exits locally for /quit',",
        "  })",
        "createSlashHandler.test.ts /quit regression",
    )
    require(
        "expect(ctx.session.die).toHaveBeenCalledTimes(1)" in quit_test,
        "createSlashHandler.test.ts must assert /quit exits exactly once",
    )

    if require_dist:
        dist = read_required(root, "ui-tui/dist/entry.js")
        require(
            "Session ${sid} ended" in dist
            and "resume with: hermes --resume ${sid}" in dist,
            "built TUI dist lacks the exit-session resume line",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, help="Hermes runtime checkout")
    parser.add_argument(
        "--require-dist",
        action="store_true",
        help="also require the compiled TUI bundle to carry the resume line",
    )
    args = parser.parse_args()

    try:
        validate(args.root.resolve(), require_dist=args.require_dist)
    except ContractError as exc:
        print(f"ERROR: exit-session patch contract broken: {exc}", file=sys.stderr)
        return 1

    suffix = " + dist" if args.require_dist else ""
    print(f"exit-session patch contract: OK{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
