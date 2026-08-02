import { writeSync } from 'node:fs'

/**
 * Print the session id on user-initiated exits (Ctrl+C / Ctrl+D when idle,
 * /quit) so the user can resume the conversation afterwards. Runs AFTER Ink's
 * unmount (normal screen restored) and writes synchronously so the line can
 * never be dropped by the process.exit() that follows.
 *
 * `emit` is injectable for tests; the default writes to fd 1 (stdout).
 */
export const emitSessionIdAtExit = (
  sid: null | string,
  emit: (text: string) => void = (text: string) => {
    writeSync(1, text)
  }
): void => {
  if (!sid) {
    return
  }

  try {
    emit(`\nSession ${sid} ended — resume with: hermes --resume ${sid}\n`)
  } catch {
    // stdout already gone (dashboard tab closed / EIO) — nothing to show
  }
}
