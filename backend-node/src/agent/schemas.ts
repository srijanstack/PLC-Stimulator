import { z } from 'zod'

/** Snapshot of the whole workbench, sent by the frontend with every question. */
export const agentContextSchema = z.object({
  project: z.string().max(200),
  running: z.boolean(),
  ladder: z
    .array(
      z.object({
        name: z.string().max(100),
        address: z.string().max(40),
        instructionId: z.string().max(60),
        instruction: z.string().max(60),
        kind: z.string().max(30)
      })
    )
    .max(60),
  hardware: z
    .array(
      z.object({
        label: z.string().max(100),
        type: z.string().max(60),
        kind: z.enum(['input', 'output']),
        address: z.string().max(40),
        signal: z.boolean()
      })
    )
    .max(100),
  inputs: z.record(z.string(), z.boolean()),
  outputs: z.record(z.string(), z.boolean())
})

export const chatRequestSchema = z.object({
  message: z.string().trim().min(1).max(4000),
  history: z
    .array(
      z.object({
        role: z.enum(['user', 'assistant']),
        content: z.string().max(4000)
      })
    )
    .max(20)
    .default([]),
  context: agentContextSchema
})

export type AgentContext = z.infer<typeof agentContextSchema>
export type ChatRequest = z.infer<typeof chatRequestSchema>
