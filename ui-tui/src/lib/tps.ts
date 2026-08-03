/**
 * Token-per-second meter for the status bar — a faithful adaptation of
 * pi-agent-flow's EMA-smoothed TPS estimator
 * (src/snapshot/runner-events.ts, `updateSmoothedTps`).
 *
 * Calculation: streamed text deltas are converted to tokens with a 4:1 char
 * heuristic, accumulated in a pending bucket, and only converted to a rate
 * once MIN_TPS_SAMPLE_MS has elapsed. The instantaneous rate is capped
 * (MAX_INSTANT_TPS suppresses burst artifacts from a single large chunk) and
 * EMA-smoothed (EMA_ALPHA), with outlier damping (alpha × 0.3 when a sample
 * exceeds 2× the smoothed value) so the readout runs evenly instead of
 * jumping between chunks.
 *
 * Hermes adaptation over pi: a gap longer than STALE_WINDOW_MS (tool
 * execution, thinking, user pause) restarts the measurement window instead of
 * dividing the rate across idle time — the meter holds its last value while
 * the model works silently and only moves from real streaming.
 */

export const CHARS_PER_TOKEN = 4
export const MIN_TPS_SAMPLE_MS = 250
export const MAX_INSTANT_TPS = 300
export const EMA_ALPHA = 0.35
export const OUTLIER_DAMP_FACTOR = 0.3
export const STALE_WINDOW_MS = 3000

export interface TpsTracker {
  /** Feed a streamed text delta; chars are converted to tokens. */
  sample(chars: number, now?: number): void
  /** Feed an exact token count (e.g. a real usage delta). */
  sampleTokens(tokens: number, now?: number): void
  /** Current EMA-smoothed tokens/sec (0 = no samples yet). */
  read(): number
  /** Drop all measurement state (session switch / new turn). */
  reset(now?: number): void
}

export function createTpsTracker(): TpsTracker {
  let smoothedTps = 0
  // null = never seeded (or reset); a numeric value is the last sample time.
  let lastEmitTime: number | null = null
  let pendingTokens = 0

  const emit = (now: number) => {
    if (lastEmitTime === null) {
      // First sample after a reset — seed the clock only; the pending
      // tokens stay in the bucket so the first window measures them.
      lastEmitTime = now

      return
    }

    const deltaMs = now - lastEmitTime

    if (deltaMs < MIN_TPS_SAMPLE_MS) {
      return
    }

    // No streaming for longer than the stale window (tool execution,
    // thinking, gap between turns). Restart the window WITHOUT touching the
    // smoothed value — the rate must not be divided across idle time.
    if (deltaMs > STALE_WINDOW_MS) {
      lastEmitTime = now
      pendingTokens = 0

      return
    }

    if (pendingTokens <= 0) {
      lastEmitTime = now

      return
    }

    const deltaSec = deltaMs / 1000
    let instantRate = pendingTokens / deltaSec

    if (instantRate > MAX_INSTANT_TPS) {
      instantRate = MAX_INSTANT_TPS
    }

    if (smoothedTps === 0) {
      smoothedTps = instantRate
    } else {
      // Outlier rejection: dampen burst spikes that would dominate the EMA.
      const alpha = instantRate > 2 * smoothedTps ? EMA_ALPHA * OUTLIER_DAMP_FACTOR : EMA_ALPHA
      smoothedTps = alpha * instantRate + (1 - alpha) * smoothedTps
    }

    lastEmitTime = now
    pendingTokens = 0
  }

  return {
    sample(chars, now = Date.now()) {
      if (chars <= 0) {
        return
      }

      pendingTokens += Math.max(1, Math.round(chars / CHARS_PER_TOKEN))
      emit(now)
    },

    sampleTokens(tokens, now = Date.now()) {
      if (tokens <= 0) {
        return
      }

      pendingTokens += tokens
      emit(now)
    },

    read() {
      return smoothedTps
    },

    reset() {
      smoothedTps = 0
      lastEmitTime = null
      pendingTokens = 0
    }
  }
}

/**
 * Fixed-width tokens-per-second label (pi-agent-flow `formatTps`): one
 * decimal, left-padding to 5 columns so the readout never shifts the
 * surrounding text as the number changes width (` 45.2` vs `  9.8`).
 */
export function formatTps(value: number): string {
  if (!value || value <= 0) {
    return '----- t/s'
  }

  return `${value.toFixed(1).padStart(5)} t/s`
}
