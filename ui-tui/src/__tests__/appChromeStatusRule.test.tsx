import React from 'react'
import { describe, expect, it } from 'vitest'

import { $tpsTarget } from '../app/tpsStore.js'
import { StatusRule, TPS_MIN_COLS, WATER_CELL_COUNT, waterFrame } from '../components/appChrome.js'
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

  it('uses a blood-red water wave only while speculative compaction is pending or active', () => {
    const queued = findWaterTicker(StatusRule({ ...baseProps, speculativeCompressionState: 'queued' }))
    const preparing = findWaterTicker(StatusRule({ ...baseProps, speculativeCompressionState: 'preparing' }))
    const active = findWaterTicker(StatusRule({ ...baseProps, speculativeCompressionState: 'active' }))
    const installed = findWaterTicker(StatusRule({ ...baseProps, speculativeCompressionState: 'installed' }))

    expect(queued?.props.color).toBe('#B22222')
    expect(preparing?.props.color).toBe('#B22222')
    expect(active?.props.color).toBe('#B22222')
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

  it('flushes the water ticker to blood red while speculative compaction is pending', () => {
    // The optimizing-ctx label was removed; the water wave is the sole
    // pending-compaction indicator and turns blood red while it runs.
    for (const state of ['queued', 'preparing', 'active'] as const) {
      const element = StatusRule({ ...baseProps, speculativeCompressionState: state })

      const meter = findByName(element, 'WaterTicker') as React.ReactElement<{
        busy: boolean
        color: string
      }> | null

      expect(meter).not.toBeNull()
      expect(meter?.props.color).toBe('#B22222')
    }

    const idleMeter = findByName(StatusRule(baseProps), 'WaterTicker') as React.ReactElement<{
      busy: boolean
      color: string
    }> | null

    expect(idleMeter?.props.color).not.toBe('#B22222')
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
