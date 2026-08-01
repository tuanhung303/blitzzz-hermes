# Blitzzz Hermes configuration snapshot

Versioned, non-secret snapshot of the active personal Hermes setup.

## Contents

- `display.yaml` — active display, status-bar, and spacing-related settings.
- `runtime.yaml` — non-secret model, terminal, agent, memory, delegation, compression, and tool settings.
- `skins/pi.yaml` — grayscale Pi skin, including transparent status bar and static spinner.
- `tui-theme-boot.json` — resolved TUI boot theme derived from the active skin.
- `profile/USER.md` and `profile/SOUL.md` — personal instruction/profile files.

The accompanying `ui-tui/src/components/appChrome.tsx` change is the active fixed-width footer: a 25-cell Braille water raster plus model, effort, and context. Its focused test is `ui-tui/src/__tests__/appChromeStatusRule.test.tsx`.

## Applying

Merge the YAML into `~/.hermes/config.yaml`; do not replace the live file wholesale. Copy the skin to `~/.hermes/skins/pi.yaml`, then restart Hermes. Copy the profile documents to the corresponding files beneath `~/.hermes/` only when intentionally restoring this personal setup.

## Deliberate exclusions

No `.env`, `auth.json`, provider API keys, gateway tokens, session transcripts, or runtime caches are stored here. `runtime.yaml` contains only non-secret settings.
