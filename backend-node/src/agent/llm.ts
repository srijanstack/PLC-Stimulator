export type ChatMessage = {
  role: 'system' | 'user' | 'assistant'
  content: string
}

/** Anything that can answer a chat. Tests plug in a fake; production uses the HTTP client below. */
export interface LlmClient {
  chat(messages: ChatMessage[]): Promise<string>
}

/** The model server is down, slow, or returned something unusable. */
export class LlmUnavailableError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options)
    this.name = 'LlmUnavailableError'
  }
}

export type LlmConfig = {
  baseUrl: string
  model: string
  apiKey: string
  timeoutMs: number
  temperature: number
}

/**
 * Talks to any OpenAI-compatible server: Ollama, LM Studio, vLLM,
 * llama.cpp server, or a hosted API.
 */
export class OpenAiCompatibleClient implements LlmClient {
  constructor(private readonly cfg: LlmConfig) {}

  async chat(messages: ChatMessage[]): Promise<string> {
    const base = this.cfg.baseUrl.replace(/\/+$/, '')
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    }
    if (this.cfg.apiKey) headers.Authorization = `Bearer ${this.cfg.apiKey}`

    let response: Response
    try {
      response = await fetch(`${base}/chat/completions`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          model: this.cfg.model,
          messages,
          temperature: this.cfg.temperature,
          stream: false
        }),
        signal: AbortSignal.timeout(this.cfg.timeoutMs)
      })
    } catch (cause) {
      throw new LlmUnavailableError(`Could not reach the LLM server at ${base}.`, { cause })
    }

    if (!response.ok) {
      const detail = (await response.text().catch(() => '')).slice(0, 300)
      throw new LlmUnavailableError(
        `The LLM server answered ${response.status}${detail ? `: ${detail}` : ''}`
      )
    }

    let data: { choices?: { message?: { content?: unknown } }[] }
    try {
      data = (await response.json()) as typeof data
    } catch (cause) {
      throw new LlmUnavailableError('The LLM server sent an unreadable reply.', { cause })
    }

    const content = data.choices?.[0]?.message?.content
    // Reasoning models sometimes prepend <think>...</think>; the user doesn't need it.
    const text =
      typeof content === 'string'
        ? content.replace(/<think>[\s\S]*?<\/think>/g, '').trim()
        : ''
    if (!text) throw new LlmUnavailableError('The LLM returned an empty reply.')
    return text
  }
}
