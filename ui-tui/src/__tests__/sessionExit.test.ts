import { describe, expect, it, vi } from 'vitest'

import { emitSessionIdAtExit } from '../lib/sessionExit.js'

describe('emitSessionIdAtExit', () => {
  it('emits the session id with a resume hint', () => {
    const emit = vi.fn()

    emitSessionIdAtExit('abc123', emit)

    expect(emit).toHaveBeenCalledTimes(1)
    expect(emit).toHaveBeenCalledWith('\nSession abc123 ended — resume with: hermes --resume abc123\n')
  })

  it('stays silent when there is no active session', () => {
    const emit = vi.fn()

    emitSessionIdAtExit(null, emit)

    expect(emit).not.toHaveBeenCalled()
  })

  it('tolerates a dead stdout (EIO / closed dashboard tab) without throwing', () => {
    const boom = vi.fn(() => {
      throw new Error('EIO')
    })

    expect(() => emitSessionIdAtExit('abc123', boom)).not.toThrow()
  })
})
