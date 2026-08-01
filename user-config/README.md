# Blitzzz Hermes configuration snapshot

Versioned, non-secret snapshot of the active personal Hermes setup.

## Contents

- `display.yaml` — active display, status-bar, and spacing-related settings.
- `runtime.yaml` — non-secret model, terminal, agent, memory, delegation, compression, and tool settings.
- `skins/pi.yaml` — grayscale Pi skin, including transparent status bar and static spinner.
- `tui-theme-boot.json` — resolved TUI boot theme derived from the active skin.
- `profile/USER.md` and `profile/SOUL.md` — personal instruction/profile files.

The accompanying `ui-tui/src/components/appChrome.tsx` change is the active fixed-width footer: a 25-cell Braille water raster plus model, effort, and context. Its focused test is `ui-tui/src/__tests__/appChromeStatusRule.test.tsx`.

## Source of truth: change here first

`user-config/` is a tracked recovery snapshot; Hermes does not load it at
runtime. Make the intended change in the live source, verify it, then mirror
the changed non-secret files here in the same commit.

| Change | Live source to edit | Tracked mirror |
| --- | --- | --- |
| Display/status-bar settings | `~/.hermes/config.yaml` via `hermes config set display.<key> <value>` | `display.yaml` |
| Non-secret runtime settings | `~/.hermes/config.yaml` via `hermes config set <key> <value>` | `runtime.yaml` |
| Colors, spinner, tool glyphs | `~/.hermes/skins/pi.yaml` | `skins/pi.yaml` |
| Fixed water footer and spacing | `~/.hermes/hermes-agent/ui-tui/src/components/appChrome.tsx` | `ui-tui/src/components/appChrome.tsx` plus its focused test |
| Personal instructions | `~/.hermes/memories/USER.md` and `~/.hermes/SOUL.md` | `profile/USER.md` and `profile/SOUL.md` |
| Generated TUI theme | do not edit directly; it is regenerated from the active skin | `tui-theme-boot.json` |

Restart Hermes after a config or source change. For an intentional restore,
merge YAML into `~/.hermes/config.yaml` rather than replacing it wholesale,
then copy the skin/profile files to their live paths.

## Normal update and git workflow

1. Start cleanly: run `git status --short`. If there is unrelated work, keep it
   out of this change (separate branch/worktree, commit, or stash it first).
2. Edit the live source in the table above and verify the running result.
3. Mirror only the changed, non-secret file(s) into `user-config/`; update the
   corresponding `ui-tui` source and test when the footer behavior changes.
4. Validate before staging:

   ```bash
   cd /Users/__blitzzz/Documents/GitHub/blitzzz-hermes
   git diff --check
   cd ui-tui && npm run build:ink && npm test -- appChromeStatusRule.test.tsx && npm run typecheck
   ```

5. Review and stage narrowly—never use `git add -A` for this snapshot:

   ```bash
   cd /Users/__blitzzz/Documents/GitHub/blitzzz-hermes
   git diff -- user-config ui-tui/src/components/appChrome.tsx ui-tui/src/__tests__/appChromeStatusRule.test.tsx
   git add -- user-config ui-tui/src/components/appChrome.tsx ui-tui/src/__tests__/appChromeStatusRule.test.tsx
   git diff --cached --check
   git commit -m "chore(config): update personal Hermes profile"
   git push origin HEAD
   ```

Never stage `.env`, `auth.json`, gateway state, session transcripts, or caches.

## Deliberate exclusions

No `.env`, `auth.json`, provider API keys, gateway tokens, session transcripts, or runtime caches are stored here. `runtime.yaml` contains only non-secret settings.
