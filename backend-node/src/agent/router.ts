import { Router } from 'express'
import type { LlmClient } from './llm.js'
import { LlmUnavailableError } from './llm.js'
import { buildMessages } from './prompt.js'
import { chatRequestSchema } from './schemas.js'

/** POST /chat  { message, history?, context }  ->  { reply } */
export function agentRouter(llm: LlmClient) {
  const router = Router()

  router.post('/chat', async (req, res) => {
    const parsed = chatRequestSchema.safeParse(req.body)
    if (!parsed.success) {
      const detail = parsed.error.issues
        .map(i => `${i.path.join('.') || 'body'}: ${i.message}`)
        .join('; ')
      res.status(422).json({ detail })
      return
    }

    try {
      const reply = await llm.chat(buildMessages(parsed.data))
      res.json({ reply })
    } catch (error) {
      if (!(error instanceof LlmUnavailableError)) throw error
      console.warn(`[agent] ${error.message}`)
      // Still HTTP 200 so the UI shows a readable message instead of a failure.
      res.json({
        reply:
          "I can't reach the language model right now, so I can't answer that yet. " +
          'Start your model server (for Ollama: `ollama serve`, then `ollama pull <model>`) ' +
          'and check LLM_BASE_URL / LLM_MODEL in backend-node/.env.\n\n' +
          `Details: ${error.message}`,
        error: 'llm_unavailable'
      })
    }
  })

  return router
}
