import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { createApp } from '../src/app.js'
import type { ChatMessage, LlmClient } from '../src/agent/llm.js'
import type { AgentContext } from '../src/agent/schemas.js'

export class FakeLlm implements LlmClient {
  calls: ChatMessage[][] = []
  constructor(private readonly behaviour: string | Error = 'fake reply') {}

  async chat(messages: ChatMessage[]): Promise<string> {
    this.calls.push(messages)
    if (this.behaviour instanceof Error) throw this.behaviour
    return this.behaviour
  }
}

export function makeApp(llm: FakeLlm = new FakeLlm()) {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'plc-backend-'))
  return { app: createApp({ llm, dataDir, corsOrigins: ['http://localhost:5173'] }), dataDir, llm }
}

export const demoContext = (): AgentContext => ({
  project: 'Motor Control Project',
  running: true,
  ladder: [
    { name: 'Start_PB', address: 'I0.0', instructionId: 'contact_no', instruction: 'NO Contact', kind: 'contact' },
    { name: 'Motor_Running', address: 'Q0.0', instructionId: 'coil_output', instruction: 'Output Coil', kind: 'coil' }
  ],
  hardware: [
    { label: 'Start_PB', type: 'Pushbutton (NO)', kind: 'input', address: 'I0.0', signal: false },
    { label: 'Motor', type: 'Motor', kind: 'output', address: 'Q0.0', signal: false }
  ],
  inputs: {},
  outputs: {}
})
