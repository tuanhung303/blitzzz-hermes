import { beforeEach, describe, expect, it, vi } from 'vitest'

import { turnController } from '../app/turnController.js'
import { resetTurnState } from '../app/turnStore.js'
import { patchUiState, resetUiState } from '../app/uiStore.js'
import { appendTranscriptMessage } from '../lib/messages.js'
import type { Msg } from '../types.js'

// Regression test for the mid-turn ordering inversion: when a user submits
// a message while a tool loop is still in flight (busy-input
// interrupt/redirect), the old turn's tool trail must end up ABOVE the new
// user bubble — not flushed below it by the redirected turn's
// message.complete. Chronology: tool.start → tool.complete → busy user
// submit → message.complete must render trail, then user, then output.
describe('mid-turn submit ordering', () => {
  beforeEach(() => {
    resetUiState()
    resetTurnState()
    turnController.fullReset()
    patchUiState({ showReasoning: true, sid: 'test-session' })
  })

  const runTool = (toolId: string, name: string) => {
    turnController.recordToolStart(toolId, name, 'context')
    turnController.recordToolComplete(toolId, name, undefined, 'done', 10)
  }

  it('settles the in-flight tool trail above a busy user bubble', () => {
    // Old turn: start a tool loop, complete one tool.
    turnController.startMessage()
    runTool('tool-1', 'terminal')

    // User submits mid-tool-loop → the checkpoint must hand the observed
    // trail back so the caller appends it BEFORE the bubble.
    const settled = turnController.checkpointBeforeUserBubble()
    expect(settled.length).toBeGreaterThan(0)

    let transcript: Msg[] = []

    for (const msg of settled) {
      transcript = appendTranscriptMessage(transcript, msg)
    }

    const userIdx = transcript.length
    transcript = appendTranscriptMessage(transcript, { role: 'user', text: 'hold on' })

    // The redirected turn's message.complete only appends what happens
    // AFTER the interjection — the old trail must not reappear below.
    const { finalMessages } = turnController.recordMessageComplete({ text: 'adjusted' })
    transcript = [...transcript, ...finalMessages]

    const trailIdx = transcript.findIndex(msg => msg.kind === 'trail' && msg.tools?.length)
    const bubbleIdx = transcript.findIndex(msg => msg.role === 'user' && msg.text === 'hold on')
    const finalIdx = transcript.findIndex(msg => msg.role === 'assistant' && msg.text === 'adjusted')

    expect(trailIdx).toBeGreaterThanOrEqual(0)
    expect(bubbleIdx).toBeGreaterThan(trailIdx)
    expect(userIdx).toBeGreaterThan(trailIdx)
    expect(finalIdx).toBeGreaterThan(bubbleIdx)
  })

  it('leaves a fresh thread untouched when nothing is in flight', () => {
    turnController.startMessage()
    const settled = turnController.checkpointBeforeUserBubble()

    expect(settled).toEqual([])

    let transcript: Msg[] = []

    for (const msg of settled) {
      transcript = appendTranscriptMessage(transcript, msg)
    }

    transcript = appendTranscriptMessage(transcript, { role: 'user', text: 'first message' })
    expect(transcript).toHaveLength(1)
    expect(transcript[0]).toEqual({ role: 'user', text: 'first message' })
  })

  it('returns nothing after the turn already settled (interrupt path)', () => {
    turnController.startMessage()
    runTool('tool-1', 'terminal')

    // Simulate a Stop: interruptTurn flushes segments itself.
    const { appendMessage, gw, sid, sys } = {
      appendMessage: vi.fn(),
      gw: { request: vi.fn(async () => ({})) },
      sid: 'test-session',
      sys: vi.fn()
    }

    turnController.interruptTurn({ appendMessage, gw, sid, sys })

    expect(turnController.checkpointBeforeUserBubble()).toEqual([])
  })
})
