import { atom } from 'nanostores'

import { createTpsTracker, type TpsTracker } from '../lib/tps.js'

/**
 * Status-bar TPS meter state.
 *
 * A module-level singleton is enough: the TUI drives one active session at a
 * time, and the gateway event handler resets the tracker whenever a
 * `message.delta` arrives for a different session_id. The atom holds the
 * EMA-smoothed target; the animated readout (TpsMeter in appChrome) eases
 * toward it so the number rolls evenly instead of snapping between samples.
 */
const tracker: TpsTracker = createTpsTracker()

export const $tpsTarget = atom(0)

/** Feed streamed assistant text (chars). `now` is injectable for tests. */
export const feedTpsChars = (chars: number, now: number = Date.now()): void => {
  if (chars <= 0) {
    return
  }

  tracker.sample(chars, now)
  const value = tracker.read()

  if (value !== $tpsTarget.get()) {
    $tpsTarget.set(value)
  }
}

/** Reset all measurement state (session switch). */
export const resetTps = (): void => {
  tracker.reset()
  $tpsTarget.set(0)
}
