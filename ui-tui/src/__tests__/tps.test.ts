import { describe, expect, it } from 'vitest'

import {
  CHARS_PER_TOKEN,
  createTpsTracker,
  EMA_ALPHA,
  formatTps,
  MAX_INSTANT_TPS,
  MIN_TPS_SAMPLE_MS,
  OUTLIER_DAMP_FACTOR,
  STALE_WINDOW_MS
} from '../lib/tps.js'

// Deterministic clock: the tracker accepts an explicit `now`, so tests drive
// time without fake timers.
let clock = 0
const now = () => clock

const advance = (ms: number) => {
  clock += ms
}

// Feed `ticks` samples of `charsPerTick` chars, each spaced just past the
// minimum measurement window. Each tick constitutes its own measurement
// window (pending resets after every emit), so the steady state converges on
// `charsPerTick / CHARS_PER_TOKEN` tokens per `spacingMs`.
const feedCharsAtRate = (
  tracker: ReturnType<typeof createTpsTracker>,
  charsPerTick: number,
  ticks: number,
  spacingMs: number = MIN_TPS_SAMPLE_MS + 10
) => {
  for (let i = 0; i < ticks; i += 1) {
    advance(spacingMs)
    tracker.sample(charsPerTick, now())
  }
}

describe('createTpsTracker', () => {
  it('reads 0 before any sample', () => {
    const tracker = createTpsTracker()

    expect(tracker.read()).toBe(0)
  })

  it('seeds the clock on the first sample and emits nothing', () => {
    const tracker = createTpsTracker()
    tracker.sample(100, now())

    expect(tracker.read()).toBe(0)
  })

  it('measures the first window including its seed tokens', () => {
    const tracker = createTpsTracker()

    // Seed: 200 chars → 50 tokens arrive at t=0 (window start while seeding).
    tracker.sample(200, now())
    // 1s later 400 chars → +100 tokens: 150 tokens / 1s = 150 t/s.
    advance(1000)
    tracker.sample(400, now())

    expect(tracker.read()).toBeCloseTo(150, 0)
  })

  it('accumulates rapid sub-window samples before emitting', () => {
    const tracker = createTpsTracker()
    tracker.sample(120, now()) // +30 tokens (seed)
    advance(50)
    tracker.sample(160, now()) // +40 tokens
    advance(50)
    tracker.sample(200, now()) // +50 tokens → 120 pending in 100ms

    expect(tracker.read()).toBe(0)

    // 500ms later one more sample fires the window: 130 tokens / 0.6s ≈ 217.
    advance(500)
    tracker.sampleTokens(10, now())
    expect(tracker.read()).toBeCloseTo(130 / (600 / 1000), 0)
  })

  it('EMA-smooths a steady stream toward the true rate, capped below the burst limit', () => {
    const tracker = createTpsTracker()

    // 200 chars (50 tokens) per 260ms ≈ 192 t/s sustained — the second
    // window includes the seed tokens, so the readout converges toward 192
    // from above and never exceeds MAX_INSTANT_TPS.
    feedCharsAtRate(tracker, 200, 8)

    const rate = tracker.read()
    expect(rate).toBeGreaterThan(0)
    expect(rate).toBeLessThanOrEqual(MAX_INSTANT_TPS)
  })

  it('damps outlier bursts harder than steady samples', () => {
    const tracker = createTpsTracker()
    // Small steady stream: 100 chars (25 tokens) per 260ms ≈ 96 t/s. After
    // 12 ticks the EMA has converged to ~98.
    feedCharsAtRate(tracker, 100, 12)
    const steady = tracker.read()
    expect(steady).toBeLessThan(130)

    // One 3× burst (300 chars) in a single tick → instant ≈ 288 t/s, which
    // is more than 2× the steady value — the damped alpha must apply.
    advance(MIN_TPS_SAMPLE_MS + 10)
    tracker.sample(300, now())

    const instantRate = 75 / ((MIN_TPS_SAMPLE_MS + 10) / 1000)
    const undamped = steady * (1 - EMA_ALPHA) + instantRate * EMA_ALPHA
    const damped = steady * (1 - EMA_ALPHA * OUTLIER_DAMP_FACTOR) + instantRate * EMA_ALPHA * OUTLIER_DAMP_FACTOR

    expect(tracker.read()).toBeCloseTo(damped, 0)
    expect(tracker.read()).toBeLessThan(undamped)
    expect(tracker.read()).toBeGreaterThan(steady)
  })

  it('freezes across a stale gap (tool execution) instead of dividing by idle time', () => {
    const tracker = createTpsTracker()
    feedCharsAtRate(tracker, 200, 2)
    const before = tracker.read()
    expect(before).toBeGreaterThan(0)

    // Tool loop: no samples for longer than STALE_WINDOW_MS.
    advance(STALE_WINDOW_MS + 5000)
    tracker.sample(200, now())

    // The gap must not drag the rate down — the value holds (the window is
    // restarted, so the post-gap sample is measured on its own).
    expect(tracker.read()).toBe(before)

    // The next stream after the gap keeps measuring from the fresh window.
    feedCharsAtRate(tracker, 200, 4)
    expect(tracker.read()).toBeGreaterThan(0)
  })

  it('reset drops the smoothed value and restarts measurement', () => {
    const tracker = createTpsTracker()
    feedCharsAtRate(tracker, 200, 2)
    expect(tracker.read()).toBeGreaterThan(0)

    tracker.reset(now())
    expect(tracker.read()).toBe(0)

    // First sample after reset only re-seeds the clock.
    tracker.sample(200, now())
    expect(tracker.read()).toBe(0)
  })

  it('ignores non-positive samples but lets their ticks fire the window', () => {
    const tracker = createTpsTracker()
    tracker.sample(0, now())
    tracker.sample(-10, now())
    tracker.sampleTokens(0, now())

    expect(tracker.read()).toBe(0)
  })

  it('sampleTokens feeds exact token counts through the same EMA', () => {
    const tracker = createTpsTracker()
    feedCharsAtRate(tracker, 200, 3)
    const before = tracker.read()

    advance(MIN_TPS_SAMPLE_MS + 10)
    tracker.sampleTokens(1000, now())

    expect(tracker.read()).toBeGreaterThan(before)
  })

  it('converts chars to tokens with the 4:1 heuristic', () => {
    const tracker = createTpsTracker()
    tracker.sample(400, now()) // seed: 100 tokens
    advance(1000)
    tracker.sample(4, now()) // +1 token, fires a 1s window

    expect(tracker.read()).toBeCloseTo(101 / (1000 / 1000), 0)
    expect(tracker.read()).toBeCloseTo(400 / CHARS_PER_TOKEN + 1, 0)
  })
})

describe('formatTps', () => {
  it('formats with one decimal, padded to a fixed 5-char width', () => {
    expect(formatTps(45.234)).toBe(' 45.2 t/s')
    expect(formatTps(9.8)).toBe('  9.8 t/s')
    expect(formatTps(300)).toBe('300.0 t/s')
    expect(formatTps(0.05)).toBe('  0.1 t/s')
  })

  it('renders a placeholder for absent values', () => {
    expect(formatTps(0)).toBe('----- t/s')
    expect(formatTps(-1)).toBe('----- t/s')
  })

  it('keeps constant width so surrounding status text never shifts', () => {
    const widths = new Set(['0.05', '9.8', '45.2', '300'].map(v => formatTps(Number(v)).length))
    expect(widths.size).toBe(1)
  })
})
