# Hermes maintenance: safety + performance plan

**Status:** decision-ready, no changes made.  
**Scope:** live read-only audit of the default profile, managed runtime, patch-set repository, cron state, and the supplied round-one tail. No `.env`, credentials, updates, restarts, or cron mutations were read or performed.

## Verified final state

A maintenance **audit** is successful only when it proves, in an isolated candidate, that the complete declared customization surface applies to the pinned upstream revision, its class-specific behavioral tests and generated TUI artifact pass, and its non-secret configuration mirrors are either equal or explicitly reported as drift. It must emit a run ID plus per-row status/duration; it must **not** update, restart, reset, checkout, clean, copy configuration, or rewrite memory.

A separate, explicitly approved **apply** operation may update only after a reproducible rollback artifact has been created and restored successfully in a disposable clone. A failure is fail-closed: retain the live runtime and report the failed row.

This splits the current combined update/recovery/memory-distillation job into deterministic safety-critical maintenance and an optional, separately governed memory task. It reduces latency by removing the LLM from deterministic work, not by deleting tests or lowering reasoning globally.

## Evidence ledger and reconciled current state

### Observed live job state

| Field | Observed value | Evidence |
|---|---|---|
| Profile | `default`, gateway running | `hermes profile list` read-only result |
| Job | `hermes-daily-maintenance` / `de6e446cf2c5` | `~/.hermes/cron/jobs.json:1` parsed read-only |
| Mode | agent (`no_agent=false`), not a script job | `jobs.json:1`; scheduler distinguishes no-agent at `cron/scheduler.py:3176-3198` |
| Schedule | `0 4 * * *`, next `2026-08-10T04:00:00+07:00` | `jobs.json:1` parsed read-only |
| Model/provider | `gpt-5.6-luna` / `openai-codex` | `jobs.json:1` parsed read-only |
| Reasoning/service tier | job has no own override; config resolves Luna to `max` and `fast` | `~/.hermes/config.yaml:45-51`; resolver precedence `hermes_constants.py:1100-1157`; cron passes it to the agent at `cron/scheduler.py:3933-3935,4045-4065` |
| Toolsets | `enabled_toolsets=[terminal,file]` | `jobs.json:1` parsed read-only; per-job precedence `cron/scheduler.py:223-253` |
| Workdir | unset; therefore project context files are skipped | `jobs.json:1`; `cron/scheduler.py:4067-4073` |
| Delivery | `all`, no origin, last delivery error null | `jobs.json:1` parsed read-only |
| Last four durations | 258.1s, 403.9s, 411.6s, 67.5s | read-only `~/.hermes/cron/executions.db`; schema timestamps at `cron/executions.py:40-53` |

### Resolved contradictions

1. **“3-minute hard interrupt” is stale documentation, not live behavior.** `AGENTS.md:1111-1114` says three minutes; the ledger proves 403.9s and 411.6s executions completed. The live scheduler instead describes a 600s *inactivity* timeout at `cron/scheduler.py:4080-4089`. Treat the ledger plus source as authoritative until the document is corrected.
2. **“Daily watchdog uses executable verifier” is only true for exit-session.** The README claims that broad property (`README.md:34-40`), but `surface_ok()` checks three markers plus the exit verifier only (`~/.hermes/scripts/hermes-maintenance.sh:16-21`). The 82 active paths span substantially more than those legs.
3. **The patch surface is reproducible by content today, not fully validated by behavior.** A read-only disposable-candidate comparison proved **82/82 active patch paths byte-equivalent** to current managed content. The active patches themselves list 73 + 9 path sections. This removes the claim that the current dirty surface is path-unreproducible; it does not prove every customization is behaviorally valid after new upstream code.
4. **Pre-update backup is enabled as full, but it is not source custody.** Active config requests `pre_update_backup: 'true'` (`~/.hermes/config.yaml:629-631`), which resolves to full (`hermes_cli/update_cmd.py:2514-2556`). The backup excludes root `hermes-agent` explicitly (`hermes_cli/backup.py:55-75,300-325`), so it cannot be the rollback artifact for the managed source.
5. **`deliver=all` is dynamic fan-out, not an end-to-end receipt.** It expands at runtime to every configured home channel (`cron/scheduler.py:1427-1457`). The scheduler records a send result as `delivered` when no error is returned (`cron/scheduler.py:4697-4711`); adapter confirmation means only an explicit `success` field (`:1528-1546`). No execution-table per-target message ID/receipt was observed.
6. **`xhigh` is not verified as the daily job’s main-reasoning bottleneck.** Luna is configured at `max` (`config.yaml:45-51`). `xhigh` is observed on *auxiliary compression* (`config.yaml:203-212`), not on the job itself. Changing either global reasoning or compression reasoning is out of scope until a trace ties it to run time.

## Findings, severity, and strongest counterarguments

| Priority | Finding | Direct evidence | Strongest counterargument / decision |
|---|---|---|---|
| **P0** | Automatic recovery can erase a dirty managed tree without a verified source rollback. | `hermes-maintenance.sh:52-58` runs `git reset`, `git checkout -- .`, and `git clean -fdq`; the normal updater restarts gateways after update (`hermes_cli/update_cmd.py:4861-4900`). Full backup excludes source. | The current 82 paths reproduce from patches today. That is helpful but insufficient: no pre-destructive, versioned, restore-tested custody gate exists. Block automatic update/recovery. |
| **P0** | Maintenance can report a healthy surface while custom classes are untested. | `surface_ok()` only covers `tpsStore`, `waterFrameStep`, gateway throughput marker, and exit contract (`hermes-maintenance.sh:16-21`). Active patches cover 82 paths. | Exit contract is unusually strong: 18 mutation probes passed in this audit. It remains a narrow class, not coverage of compression, runtime budget, TUI state, gateway, or config mirrors. |
| **P0** | Agent-mode maintenance has an unbounded total wall time relative to stale docs and combines unrelated mutation. | Actual executions exceed 3 minutes; current prompt combines runtime maintenance with memory distillation; scheduler loads an AIAgent and toolsets (`cron/scheduler.py:4045-4075`). | It uses pinned provider/model/toolsets, and all last recorded runs were `ok`. Pinning prevents drift but not latency or destructive tool use. |
| **P1** | Delivery cannot prove receipt at a fixed destination. | Job uses `all`; delivery targets are late-bound; only last delivery error is stored in job metadata. | Explicit adapter `success` improves transport confidence. It is still not a per-target immutable receipt. |
| **P1** | Tracked user-config recovery mirror is stale on observed safe fields. | Live model is Sol (`config.yaml:1-5`) versus mirror Terra (`user-config/runtime.yaml:1-6`); live global effort is max (`config.yaml:45`) versus mirror high (`runtime.yaml:24-27`); live `inline_diffs=false` (`config.yaml:294-299`) versus mirror true (`user-config/display.yaml:19-24`). | The mirror declares itself a recovery snapshot, not runtime source (`user-config/README.md:15-32`), so drift can be intentional. Require explicit classification, never automatic overwrite. |
| **P2** | Current verifier/output contracts lack a single machine-readable inventory. | Patch inventory is two patch files; checker is exit-specific (`scripts/check-patch-surface.py:79-263`). | Existing focused tests are fast and strong. A manifest makes their required coverage durable across update paths. |

## Mandatory `AGENTS.md` maintenance checklist matrix

Add this matrix to **`~/.hermes/hermes-agent/AGENTS.md`** and mirror its executable source of truth in a new patch-set manifest. The AGENTS table is human/agent governance; the no-agent script must consume the manifest directly and must not rely on context injection.

| Custom feature class (complete active-surface grouping) | Canonical validator every audit run | Success evidence | Failure semantics |
|---|---|---|---|
| Patch custody, 82-path inventory, patch order | New `blitzzz-hermes/scripts/verify-maintenance-surface.sh --candidate`; apply both active patches to an isolated clone; exact path/hash comparison | manifest revision, upstream HEAD, patch SHA-256, `82/82` comparison | **BLOCK APPLY/RECOVERY**; preserve live tree; report drift/incompatibility |
| Durable session ID, `/quit`, idle Ctrl+C, source-to-dist chain | Existing `tests/test-session-exit-patch-contract.sh` and `scripts/verify-exit-session-contract.sh <candidate>` | mutation suite, three focused Vitest tests, fresh bundle check | **BLOCK APPLY/RECOVERY**; no marker-only substitute |
| Context compression, pre-compression memory continuity, redaction/focus | Canonical runner for `test_context_compressor.py`, `test_pre_compress_memory_context.py`, `test_compaction_redaction_boundaries.py`, `test_compress_focus.py` | per-file counts/durations | **BLOCK APPLY/RECOVERY**; do not turn compression off as a workaround |
| Execution budget, terminal/process timeout advice, prompt injection | Canonical runner for `test_execution_budget_prompt.py`, `test_runtime_budget.py`, `test_terminal_runtime_budget.py`, `test_terminal_foreground_timeout_cap.py` | per-file counts/durations | **BLOCK APPLY/RECOVERY**; no relaxation of budget enforcement |
| TUI status/footer, TPS/wave, backpressure, submission/turn order | Manifested Vitest list containing all patch-owned `ui-tui/src/__tests__` paths; `npm run typecheck`; fresh `npm run build` | test count, typecheck, dist hash | **BLOCK APPLY/RECOVERY**; never accept only expected strings in old dist |
| Gateway/session/platform path changes | Manifested canonical Python suite for patch-owned `tests/gateway`, `tests/tui_gateway`, `tests/test_tui_gateway_server.py`, plus source-to-dist gateway test where declared | per-file result and upstream/candidate SHA | **BLOCK APPLY/RECOVERY** |
| User config, display/skin, and profile recovery mirrors | New non-secret `verify-user-config-mirror.py --report-only`; compare allowlisted YAML keys; compare profile/skin hashes without printing contents | `equal`, or explicit field/hash drift report | **NO AUTO-COPY**. Mark `DRIFT`; block automatic source-changing apply until owner classifies it |
| Maintenance scripts, manifest, AGENTS contract | `bash -n`, `PYTHONDONTWRITEBYTECODE=1 python -m py_compile`, JSON/YAML schema parse, and a mutation test proving a removed manifest row fails | static status plus negative test | **FAIL CLOSED**; no fallback to current marker-only `surface_ok()` |
| Delivery | fixed target preflight; ledger check for run ID; platform-specific query only when an authenticated read API exists | per-target send result and queried message ID where supported | If receipt cannot be queried, state `TRANSPORT-ACK ONLY`; never emit success as receipt |
| Memory distillation | separate job and separate written contract; no part of runtime update/audit | its own before/after integrity report | **ISOLATE**; a memory issue cannot trigger reset/update/recovery |

The manifest must include exact files, commands, expected artifacts, timeout, owner, and class severity. A literal marker must never satisfy a behavioral row.

## Dependency-ordered implementation plan

### P0 — stop destructive ambiguity before the next automatic run

1. **Freeze automatic source mutation.** Update `~/.hermes/scripts/hermes-maintenance.sh` so its default is `audit`, never calls `hermes update`, `git reset`, `git checkout`, `git clean`, `uv sync`, or a live-tree build. Retain mutating behavior only as an explicit `apply --approved-run-id` path. Likely files: `~/.hermes/scripts/hermes-maintenance.sh`, `blitzzz-hermes/README.md`.
2. **Create independent source custody.** Add `blitzzz-hermes/scripts/create-managed-rollback.sh` and `verify-managed-rollback.sh`. Before an approved update, archive exact managed HEAD, binary diff, untracked managed files, active patch files, and a path/hash manifest **outside** `~/.hermes/hermes-agent`; restore it into a disposable clone and prove byte equality before permitting any destructive command. Do not treat Hermes full backup as source rollback.
3. **Create an executable surface manifest and verifier.** Add `blitzzz-hermes/maintenance/surface-manifest.json` plus `scripts/verify-maintenance-surface.sh` (or Python only if shell orchestration becomes unsafe). It must drive every matrix row in an isolated clone and emit structured results including run ID and durations. Extend `tests/test-maintenance-surface-contract.sh` with removal/comment/dead-branch mutations so a missing class cannot pass.
4. **Correct governance, then package it.** Add the matrix above to `~/.hermes/hermes-agent/AGENTS.md`, amend `blitzzz-hermes/user-config/README.md` to say mirrors are report-only in unattended audit, and update `README.md` to distinguish exit-only validation from complete maintenance validation. Regenerate the active managed patch only after a clean candidate proves it.

**P0 no-go:** do not modify cron; do not run `hermes update`; do not restart gateway; do not invoke current recovery branch unless (a) custody restore passed, (b) all manifest rows pass in the candidate, (c) source/config drift is classified, and (d) a fixed delivery target has been chosen.

### P1 — make the scheduled path deterministic, bounded, and observable

1. After P0 passes, replace the current job via the supported cron API/CLI, not direct `jobs.json` edits. Set `no_agent=true`, `script=hermes-maintenance.sh`, explicit `workdir=/Users/__blitzzz/Documents/GitHub/blitzzz-hermes`, no model/provider/reasoning requirement, and the fixed audit command. Scheduler source confirms no-agent skips AIAgent/session/token machinery (`cron/scheduler.py:3176-3189`).
2. Replace `deliver=all` with one owner-approved explicit `platform:chat_id:thread_id` target. Do not guess an ID. The report must contain run ID, upstream/candidate SHA, matrix totals, elapsed time, rollback ID (if apply), and `delivery=transport-ack-only|receipt-verified`.
3. Move memory distillation to a separately named/scheduled job with its current narrow write allowlist. It must never call runtime maintenance, and runtime maintenance must never touch memory.
4. Add a post-schedule, read-only delivery verifier: inspect execution ledger, job `last_status`, `last_delivery_error`, and the target API only if it can return the emitted run ID. If platform query is unavailable, notify as transport acknowledgement, not end-to-end delivery.

**P1 no-go:** do not declare delivery verified from `last_status=ok`; do not retain agent mode solely to preserve narration; do not make a job depend on AGENTS loading when `no_agent` is used.

### P2 — measure and optimize without weakening correctness

Run each experiment against the same candidate revision and manifest; record p50/p95 wall time, peak process count, test counts, and delivery outcome. One change at a time, rollback if a required validator regresses.

| Experiment | Expected impact | Confidence | Risk/control |
|---|---:|---|---|
| Agent-mode combined job → no-agent audit, memory split out | High reduction in schedule latency and model cost; current observed runs are 67–412s | High that AIAgent/token work disappears; scheduler documents it | Validate identical matrix output and failure alerts; never remove validators |
| Candidate reuse keyed by upstream HEAD + patch hashes, invalidate on either change | Moderate cold-run reduction | Medium | Re-run full candidate validation on any hash/change; cached green cannot survive a revision change |
| Parallelize independent **read-only candidate** test classes only after baseline | Moderate reduction in wall time | Medium | Preserve per-row logs/exit codes; cap workers; no shared live workdir |
| Measure auxiliary compression separately | Potentially high only if measured as dominant | Low/unverified | Do not lower `xhigh`, Luna `max`, or global reasoning; trace first and change only that isolated auxiliary setting with fidelity regression suite |
| Skip `hermes update --check` on daily audit; use a non-writing remote-tip probe or make it an approved preflight | Small, avoids local ref mutation | High | `hermes update --check` fetches (`update_cmd.py:2200-2279`); do not call it from a no-mutation audit |

## Empirical rehearsal gates and exact commands

All are candidate-only except static state reads. Keep each individual command under three minutes; record actual wall time.

1. **Static/source/config/cron state:** `bash -n` all maintenance/apply/test scripts; `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile scripts/check-patch-surface.py`; `git diff --check`; JSON parse `~/.hermes/cron/jobs.json`; read-only `sqlite3` query of executions.
2. **Exit integration:** `bash tests/test-session-exit-patch-contract.sh` in a disposable candidate. It must include source, mutation, focused tests, fresh build, and dist validation.
3. **Compression:** canonical runner with the four compression/memory tests listed in the matrix.
4. **Runtime budget:** canonical runner with the four budget/process/prompt tests listed in the matrix.
5. **TUI:** manifested patch-owned Vitest set, `npm run typecheck`, then `npm run build`, then the dist assertion.
6. **Recovery rehearsal:** create custody archive; restore into a disposable clone; apply active patches; execute full manifest; compare every manifest path/hash; only then permit a manually approved `hermes update` in a maintenance window.
7. **Delivery rehearsal:** use a non-mutating dry delivery capability if the selected platform supports it; otherwise make one explicitly approved test delivery and query it by run ID. A send without queryable receipt stays `TRANSPORT-ACK ONLY`.

### Audit results obtained now

- Static shell/Python/cron-JSON checks: passed; both repository `git diff --check` checks passed.
- Live exit source + dist check: passed in **0.09s**.
- Isolated patch-stack + exit mutation/integration contract: passed in **11.63s**; the candidate applied both active patches and rebuilt its TUI.
- Runtime-budget focused suite: **16 passed** in **6.81s** wall.
- Compression/memory focused suite: **150 passed** in **5.74s** wall.
- TUI TPS/wave: **26 passed** in **0.77s** wall; TUI status/blocked timer: **53 passed** in **1.22s** wall.
- Current complete-surface result: **unverified** until the manifest executes every declared custom class on a fresh candidate. No claim of a full build/typecheck/lint run is made here.

## Unverified items deliberately left unresolved

- Exact configured `deliver=all` target set and end-user receipt: not queried, to avoid reading gateway credentials or sending a probe.
- Whether profile/SOUL mirror hashes match live sources: not read because this audit did not need personal-content access.
- Full TUI typecheck/lint and all patch-owned gateway tests on a fresh candidate: not run; plan makes them mandatory before apply.
- Whether auxiliary compression is a material share of maintenance latency: not measured.
- Any claim that an updater would always discard or always restore changes: update behavior remains conditional; the plan removes reliance on that condition.

## Decision

**Do not allow the present agent-mode daily job to update, reset, clean, reapply, build the live tree, restart the gateway, or mutate memory as one transaction.** Implement P0 first, then migrate to no-agent audit in P1. Preserve all current safety tests and reasoning levels; improve latency through separation, deterministic scripts, immutable candidate evidence, and cache invalidation.
