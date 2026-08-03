import { PassThrough } from 'stream'

import { renderSync } from '@hermes/ink'
import React from 'react'
import { describe, expect, it } from 'vitest'

import { $tpsTarget } from '../app/tpsStore.js'
import {
  OPTIMIZING_DOTS_WIDTH,
  optimizingLabel,
  optimizingTokensLabel,
  StatusRule,
  TPS_MIN_COLS,
  WATER_CELL_COUNT,
  waterFrame
} from '../components/appChrome.js'
import { DEFAULT_THEME, type Theme } from '../theme.js'
import type { Usage } from '../types.js'

type ReactNodeLike = React.ReactNode

const textContent = (node: ReactNodeLike): string => {
  if (node === null || node === undefined || typeof node === 'boolean') {
    return ''
  }

  if (typeof node === 'string' || typeof node === 'number') {
    return String(node)
  }

  if (Array.isArray(node)) {
    return node.map(textContent).join('')
  }

  if (React.isValidElement(node)) {
    return textContent((node as React.ReactElement<{ children?: ReactNodeLike }>).props.children)
  }

  return ''
}

const findWaterTicker = (node: ReactNodeLike): React.ReactElement<{ busy?: boolean; color?: string }> | null => {
  if (node === null || node === undefined || typeof node === 'boolean') {
    return null
  }

  if (Array.isArray(node)) {
    for (const child of node) {
      const found = findWaterTicker(child)

      if (found) {
        return found
      }
    }

    return null
  }

  if (!React.isValidElement(node)) {
    return null
  }

  const element = node as React.ReactElement<{ busy?: boolean; color?: string; children?: ReactNodeLike }>

  if (typeof element.type === 'function' && element.type.name === 'WaterTicker') {
    return element
  }

  return findWaterTicker(element.props.children)
}

const findByName = (node: ReactNodeLike, name: string): React.ReactElement | null => {
  if (node === null || node === undefined || typeof node === 'boolean') {
    return null
  }

  if (Array.isArray(node)) {
    for (const child of node) {
      const found = findByName(child, name)

      if (found) {
        return found
      }
    }

    return null
  }

  if (!React.isValidElement(node)) {
    return null
  }

  if (typeof node.type === 'function' && (node.type as () => unknown).name === name) {
    return node
  }

  return findByName(node.props.children, name)
}

const baseProps: Parameters<typeof StatusRule>[0] = {
  bgCount: 3,
  busy: false,
  cols: 100,
  cwdLabel: '~/repo',
  liveSessionCount: 2,
  model: 'openai/gpt-5.6-terra',
  modelReasoningEffort: 'high',
  notice: { key: 'credits.90', kind: 'sticky', level: 'warn', text: '⚠ 90% used' },
  sessionStartedAt: Date.now() - 60_000,
  speculativeCompressionState: 'idle',
  status: 'ready',
  statusColor: DEFAULT_THEME.color.ok,
  t: DEFAULT_THEME,
  turnStartedAt: null,
  usage: {
    active_subagents: 2,
    calls: 0,
    compressions: 3,
    context_max: 260_000,
    context_percent: 25,
    context_used: 65_000,
    input: 0,
    output: 0,
    total: 65_000
  },
  voiceLabel: 'voice off'
}

describe('waterFrame', () => {
  it('is deterministic, fixed-width, dense Braille, and evolves between frames', () => {
    const first = waterFrame(0)
    const next = waterFrame(1)

    expect(first).toHaveLength(WATER_CELL_COUNT)
    expect(first).toBe(waterFrame(0))
    expect(next).toHaveLength(WATER_CELL_COUNT)
    expect(next).not.toBe(first)
    expect([...first].filter((cell, index) => cell !== [...next][index]).length).toBeLessThan(WATER_CELL_COUNT)
    expect([...first].every(cell => cell >= '\u2800' && cell <= '\u28ff')).toBe(true)
    expect([...first].filter(cell => cell !== '\u2800')).toHaveLength(WATER_CELL_COUNT)
    expect([...waterFrame(2)]).toContain('\u2800')
  })
})

describe('StatusRule', () => {
  it('shows only water, model effort, and current/total context', () => {
    const rendered = textContent(StatusRule({ ...baseProps, usage: { ...baseProps.usage, compressions: 0 } }))

    expect(rendered).toContain('gpt 5.6 terra high')
    expect(rendered).toContain('65k/260k')
    expect(rendered).not.toContain('ready')
    expect(rendered).not.toContain('~/repo')
    expect(rendered).not.toContain('90% used')
    expect(rendered).not.toContain('cmp 3')
    expect(rendered).not.toContain('background')
    expect(rendered).not.toContain('[')
  })

  it('keeps a WaterTicker mounted for both busy and idle states so idle freezes the last frame', () => {
    const idle = findWaterTicker(StatusRule(baseProps))
    const busy = findWaterTicker(StatusRule({ ...baseProps, busy: true }))

    expect(idle?.props.busy).toBe(false)
    expect(busy?.props.busy).toBe(true)
  })

  it('uses a warm-coral water wave only while speculative compaction is pending or active', () => {
    const queued = findWaterTicker(StatusRule({ ...baseProps, speculativeCompressionState: 'queued' }))
    const preparing = findWaterTicker(StatusRule({ ...baseProps, speculativeCompressionState: 'preparing' }))
    const active = findWaterTicker(StatusRule({ ...baseProps, speculativeCompressionState: 'active' }))
    const installed = findWaterTicker(StatusRule({ ...baseProps, speculativeCompressionState: 'installed' }))

    expect(queued?.props.color).toBe('#E98572')
    expect(preparing?.props.color).toBe('#E98572')
    expect(active?.props.color).toBe('#E98572')
    expect(installed?.props.color).toBe(DEFAULT_THEME.color.muted)
  })

  it('uses a stable effort label when the session has no explicit effort', () => {
    const rendered = textContent(StatusRule({ ...baseProps, modelReasoningEffort: undefined }))

    expect(rendered).toContain('gpt 5.6 terra standard')
  })

  it('falls back to total/unknown context when the server omits a context window', () => {
    const usage: Usage = { calls: 0, input: 0, output: 0, total: 65_000 }
    const rendered = textContent(StatusRule({ ...baseProps, usage }))

    expect(rendered).toContain('65k/—')
  })
  it('shows compression count alongside Pi context after a compaction', () => {
    const rendered = textContent(StatusRule(baseProps))

    expect(rendered).toContain('gpt 5.6 terra high')
    expect(rendered).toContain('65k/260k')
    expect(rendered).toContain('cmp 3')
    expect(rendered).not.toContain('ready')
    expect(rendered).not.toContain('~/repo')
    expect(rendered).not.toContain('90% used')
    expect(rendered).not.toContain('background')
    expect(rendered).not.toContain('[')
  })

  it('hides the Pi compression count before the first compaction', () => {
    const rendered = textContent(StatusRule({ ...baseProps, usage: { ...baseProps.usage, compressions: 0 } }))

    expect(rendered).not.toContain('cmp ')
  })

  it('drops the Pi compression count before it can truncate narrow context', () => {
    const rendered = textContent(StatusRule({ ...baseProps, cols: 79 }))

    expect(rendered).toContain('65k/260k')
    expect(rendered).not.toContain('cmp 3')
  })


  it('shows the optimizing-ctx label while speculative compaction is pending', () => {
    for (const state of ['queued', 'preparing', 'active'] as const) {
      const element = StatusRule({ ...baseProps, speculativeCompressionState: state })
      expect(findByName(element, 'OptimizingCtx')).not.toBeNull()
    }

    expect(findByName(StatusRule(baseProps), 'OptimizingCtx')).toBeNull()
  })

  it('pads the optimizing-ctx dots to a constant width so the status tail never shifts', () => {
    // All 4 animation phases must occupy exactly OPTIMIZING_DOTS_WIDTH columns:
    // `...` / `..` / `.` / `   ` — the unpadded form shrank the row every tick
    // and dragged the ` │ ctx` tail (and everything after it) left/right.
    const widths = new Set([0, 1, 2, 3].map(dots => optimizingLabel(dots).length))

    expect(widths.size).toBe(1)
    expect(optimizingLabel(3)).toBe('optimizing ctx...')
    expect(optimizingLabel(0)).toBe(`optimizing ctx${' '.repeat(OPTIMIZING_DOTS_WIDTH)}`)
  })

  it('shows the summary token estimate instead of dots once the backend surfaces it', async () => {
    expect(optimizingTokensLabel(322_371)).toBe('optimizing ctx 322k')
    expect(optimizingTokensLabel(65_000)).toBe('optimizing ctx 65k')

    // OptimizingCtx owns a hook timer, so render through Ink's renderSync to
    // execute it rather than calling StatusRule as a bare function.
    const stdout = new PassThrough()
    const stdin = new PassThrough()
    const stderr = new PassThrough()

    let output = ''

    Object.assign(stdout, { columns: 100, isTTY: false, rows: 10 })
    Object.assign(stdin, { isTTY: false })
    Object.assign(stderr, { isTTY: false })
    stdout.on('data', (chunk: Buffer) => {
      output += chunk.toString()
    })

    const instance = renderSync(
      React.createElement(StatusRule, {
        ...baseProps,
        speculativeCompressionState: 'preparing',
        speculativeCompressionTokens: 322_371
      }),
      {
        patchConsole: false,
        stderr: stderr as NodeJS.WriteStream,
        stdin: stdin as NodeJS.ReadStream,
        stdout: stdout as NodeJS.WriteStream
      }
    )

    // Let Ink flush its first frame to stdout before reading the captured
    // output (same settle pattern as thinkingMoaReferenceVisibility.test.tsx).
    await new Promise(resolve => setImmediate(resolve))
    await new Promise(resolve => setImmediate(resolve))

    instance.unmount()
    instance.cleanup()

    expect(output).toContain('optimizing ctx 322k')
  })

  it('mounts the live TPS meter right after the context readout', () => {
    $tpsTarget.set(45.2)

    try {
      const meter = findByName(StatusRule(baseProps), 'TpsMeter') as React.ReactElement<{
        show: boolean
        t: Theme
      }> | null

      expect(meter).not.toBeNull()
      expect(meter?.props.show).toBe(true)
      expect(meter?.props.t).toBe(DEFAULT_THEME)
    } finally {
      $tpsTarget.set(0)
    }
  })

  it('drops the TPS meter before it can truncate narrow context', () => {
    $tpsTarget.set(45.2)

    try {
      const meter = findByName(StatusRule({ ...baseProps, cols: TPS_MIN_COLS - 1 }), 'TpsMeter') as React.ReactElement<{
        show: boolean
      }> | null

      expect(meter).not.toBeNull()
      expect(meter?.props.show).toBe(false)
    } finally {
      $tpsTarget.set(0)
    }
  })

  it('keeps the status tail quiet before the first streamed samples', () => {
    $tpsTarget.set(0)

    const element = StatusRule(baseProps)

    expect(findByName(element, 'TpsMeter')).not.toBeNull()
    expect(textContent(element)).not.toContain('t/s')
  })

})
