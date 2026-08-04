# blitzzz-hermes

Patch-set repo for the local Hermes fork surface. **No Hermes source lives
here** — this repo only carries the fork-local modifications as scripts and
patch files. The runtime is the managed install (`~/.hermes/hermes-agent`)
with the patch-set applied on top after each `hermes update`.

## Contents

| Path | Purpose |
|---|---|
| `scripts/apply-fork-to-managed.sh` | Apply the active non-spec snapshot onto the managed runtime (`--check` dry-run). It never replays the historical full fork. Run after every `hermes update`. |
| `scripts/reapply-ui-patches.sh` | Inventory the active non-spec snapshot; historical cherry-picks are disabled. |
| `scripts/upstream-sync.sh` | Old rebase pipeline for when this repo was a full fork (kept for reference). |
| `patches/fork-local-v202683.patch` | Archived full-fork export as of v2026.8.3. It is retained for historical recovery only and is never applied by the active workflow. |
| `patches/managed-current-no-spec-20260804.patch` | Active consolidated snapshot of the managed tree after speculative removal; no speculative backend/config/UI wiring is present. |

## Workflow

```bash
hermes update    # managed -> upstream (wipe local surface)
bash ~/Documents/GitHub/blitzzz-hermes/scripts/apply-fork-to-managed.sh
```

The apply script refuses a dirty managed checkout, then applies the consolidated
snapshot only when its context still matches upstream. It never replays
speculative-compression code, so upstream compression, persistent memory, and
`micro_compact` remain fully upstream-owned. After applying it re-syncs the
managed venv and rebuilds the managed TUI dist.

If the managed runtime ever needs the surface back without a full patch
apply: `~/.local/bin/hermes` is a wrapper preferring the managed runtime.

## History

The full fork history (source-code era) is preserved on origin:

- branch `full-fork-v202683`
- tag `full-fork-preclean`
