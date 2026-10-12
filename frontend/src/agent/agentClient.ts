
import type { Bits } from '../types'

const RAG_API = 'http://127.0.0.1:8001/chat'

/** Snapshot of the current PLC simulator workbench. */
export type AgentContext = {
  project: string
  running: boolean
  ladder: {
    name: string
    address: string
    instructionId: string
    instruction: string
    kind: string
    network?: number
    networkTitle?: string
  }[]
  hardware: {
    label: string
    type: string
    kind: 'input' | 'output'
    address: string
    signal: boolean
  }[]
  inputs: Bits
  outputs: Bits
}

export type HistoryMessage = {
  role: 'user' | 'assistant'
  content: string
}

type RagCitation = {
  document_title?: string
  publication_number?: string
  page_number?: number | null
  end_page_number?: number | null
  citation_str?: string
}

type RagResponse = {
  answer?: string
  citations?: RagCitation[]
}

export async function askAgent(
  message: string,
  context: AgentContext,
  history: HistoryMessage[] = []
): Promise<string> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), 130000)

  try {
    const filteredHistory = history
      .slice(-6)
      .filter(
        item =>
          !item.content.includes('do not contain sufficient evidence') &&
          !item.content.includes('does not establish this answer')
      )
      .map(
        item =>
          `${item.role === 'user' ? 'User' : 'Assistant'}: ${item.content}`
      )
      .join('\n')

    const cleanQuestion = message.trim()

    const ladderInstructions = [...new Set(context.ladder.map(item => item.instruction || item.instructionId))].filter(Boolean)

    const simulatorContext = {
      controller_model: 'Siemens S7-1200',
      routine_name: 'Main [OB1]',
      supported_instructions: ladderInstructions.length ? ladderInstructions : ['NO Contact', 'NC Contact', 'Output Coil', 'Set Bit', 'Reset Bit'],
      extra_context: {
        project: context.project,
        controller: 'Siemens S7-1200',
        routine: 'Main [OB1]',
        recent_conversation: filteredHistory || undefined,
        simulation_running: context.running,
        ladder_networks: context.ladder,
        hardware: context.hardware,
        input_bits: context.inputs,
        output_bits: context.outputs
      }
    }

    const response = await fetch(RAG_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: cleanQuestion,
        simulator_context: simulatorContext
      }),
      signal: controller.signal
    })

    const data = (await response.json().catch(() => null)) as
      | (RagResponse & { detail?: unknown; message?: string })
      | null

    if (!response.ok) {
      let errorMessage = `RAG API returned HTTP ${response.status}`
      if (typeof data?.detail === 'string') {
        errorMessage = data.detail
      } else if (Array.isArray(data?.detail)) {
        errorMessage = (data.detail as Array<{ loc?: (string | number)[]; msg?: string }>)
          .map(e => `${e.loc?.filter(x => x !== 'body').join('.') || 'field'}: ${e.msg}`)
          .join('; ')
      } else if (data?.message) {
        errorMessage = data.message
      } else if (data?.detail && typeof data.detail === 'object') {
        errorMessage = JSON.stringify(data.detail)
      }
      throw new Error(errorMessage)
    }

    if (!data || typeof data.answer !== 'string') {
      throw new Error('The RAG API returned an invalid response.')
    }

    const citations = Array.isArray(data.citations)
      ? data.citations
          .map(citation => {
            if (citation.citation_str?.trim()) {
              return citation.citation_str.trim()
            }

            const title = citation.document_title || 'PLC reference'
            const publication = citation.publication_number
            const startPage = citation.page_number
            const endPage = citation.end_page_number

            let reference = title

            if (publication) {
              reference += ` (${publication})`
            }

            if (typeof startPage === 'number') {
              reference += `, p. ${startPage}`

              if (
                typeof endPage === 'number' &&
                endPage !== startPage
              ) {
                reference += `-${endPage}`
              }
            }

            return reference
          })
          .filter(Boolean)
      : []

    const uniqueCitations = [...new Set(citations)]

    return uniqueCitations.length
      ? `${data.answer}\n\nSources:\n${uniqueCitations
          .map(citation => `- ${citation}`)
          .join('\n')}`
      : data.answer
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      return 'The RAG request timed out. Check that the chatbot API and local LLM server are running, then try again.'
    }

    const detail =
      error instanceof Error
        ? error.message
        : 'Unknown connection error'

    return `Could not get a response from the RAG chatbot.\n\n${detail}\n\nCheck that the FastAPI service is running at ${RAG_API}. No local fallback answer was generated.`
  } finally {
    window.clearTimeout(timer)
  }
}
