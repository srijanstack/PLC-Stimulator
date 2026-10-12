import { useEffect, useRef, useState } from 'react'
import { Bot, Send, Sparkles, X } from 'lucide-react'
import { createId } from '../util'
import { askAgent } from './agentClient'
import type { AgentContext } from './agentClient'

type Msg = { id: string; role: 'user' | 'assistant'; text: string }

const SUGGESTIONS = ['Explain my ladder logic', 'Check my wiring', 'Show current I/O state']

type Props = {
  /** Called when a message is sent so the agent sees the latest project. */
  getContext: () => AgentContext
  onClose: () => void
}

export default function AgentPanel({ getContext, onClose }: Props) {
  const [messages, setMessages] = useState<Msg[]>([
    {
      id: 'welcome',
      role: 'assistant',
      text: 'Hi! I can see your ladder and your hardware board. Ask me about your logic, wiring or the live I/O.'
    }
  ])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const scroller = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = scroller.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, busy])

  async function send(text: string) {
    const prompt = text.trim()
    if (!prompt || busy) return
    // Earlier turns, without the welcome message, so the model has the conversation.
    const history = messages
      .filter(m => m.id !== 'welcome')
      .slice(-10)
      .map(m => ({ role: m.role, content: m.text }))
    setMessages(prev => [...prev, { id: createId(), role: 'user', text: prompt }])
    setDraft('')
    setBusy(true)
    const reply = await askAgent(prompt, getContext(), history)
    setMessages(prev => [...prev, { id: createId(), role: 'assistant', text: reply }])
    setBusy(false)
  }

  return (
    <>
      <header className="pane-header">
        <span>
          <Bot size={15} /> AI Agent
        </span>
        <button className="icon-button" onClick={onClose} title="Hide agent">
          <X size={15} />
        </button>
      </header>

      <div className="agent-messages" ref={scroller}>
        {messages.map(m => (
          <div key={m.id} className={`msg ${m.role}`}>
            {m.text}
          </div>
        ))}
        {busy && <div className="msg assistant typing">Thinking…</div>}
      </div>

      <div className="agent-suggestions">
        {SUGGESTIONS.map(s => (
          <button key={s} onClick={() => send(s)} disabled={busy}>
            <Sparkles size={12} /> {s}
          </button>
        ))}
      </div>

      <form
        className="agent-input"
        onSubmit={e => {
          e.preventDefault()
          void send(draft)
        }}
      >
        <textarea
          value={draft}
          rows={2}
          placeholder="Ask about your logic or hardware…"
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => {
            e.stopPropagation()
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void send(draft)
            }
          }}
        />
        <button type="submit" disabled={busy || !draft.trim()} title="Send">
          <Send size={16} />
        </button>
      </form>
    </>
  )
}
