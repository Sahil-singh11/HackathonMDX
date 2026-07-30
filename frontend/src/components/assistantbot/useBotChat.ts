/**
 * Conversation state for the floating assistant.
 *
 * Two answer paths, and the UI is required to tell them apart:
 *
 *   ONLINE   POST /api/ai/chat -> hosted Gemma, grounded server-side against
 *            data/rules and given read-only tools. If the backend cannot reach
 *            Gemma it still answers, from the same rules files, and says so via
 *            `grounded_only`.
 *
 *   OFFLINE  no request is made at all. The rules JSON is bundled at build time
 *            (assistant/rulesData), so the same retrieval that grounds the
 *            server prompt runs here and the matched rules are rendered as
 *            facts. Nothing is generated, so nothing can be invented.
 *
 * The offline answer is deliberately STRUCTURED rather than prose: writing a
 * second sentence-composer in TypeScript beside the Python one in
 * app/inference/chat_grounding.py would be two things to keep true about the
 * same regulations. Rendering the retrieved rules directly cannot drift from
 * them.
 */
import { useCallback, useRef, useState } from 'react'
import { api, type ChatTurn } from '../../api/client'
import { retrieve } from '../../assistant/grounding'
import type { RuleEntry } from '../../assistant/rulesData'
import { useT } from '../../i18n'

/** Where an answer came from. Rendered as a visible chip on every bot message. */
export type AnswerSource = 'model' | 'grounded' | 'offline'

export interface BotMessage {
  id: string
  sender: 'user' | 'bot'
  text: string
  source?: AnswerSource
  /** Offline only: the retrieved rules, rendered as facts rather than prose. */
  rules?: RuleEntry[]
  /** Online: rule ids the backend answered from, for looking up in Fishing rules. */
  citedRules?: string[]
  disclosures?: string[]
  /** A controlled backend failure, shown as a note beside the answer it degraded to. */
  note?: string
  failed?: boolean
}

/** Turns sent upstream. Bounded to match the backend's MAX_HISTORY_MESSAGES. */
const MAX_HISTORY = 12

let counter = 0
const nextId = () => `m${++counter}`

export interface BotChat {
  messages: BotMessage[]
  busy: boolean
  send: (text: string) => Promise<void>
  reset: () => void
}

export function useBotChat(language: 'en' | 'mfe', online: boolean): BotChat {
  const [messages, setMessages] = useState<BotMessage[]>([])
  const [busy, setBusy] = useState(false)
  // Read inside send() so a reply that lands after a reset is still discarded.
  const generation = useRef(0)
  // useT() returns a fresh closure every render. Held in a ref so send() does
  // not have to depend on it and change identity on each render.
  const t = useT()
  const tRef = useRef(t)
  tRef.current = t

  const reset = useCallback(() => {
    generation.current += 1
    setMessages([])
    setBusy(false)
  }, [])

  const send = useCallback(async (raw: string) => {
    const text = raw.trim()
    if (!text || busy) return

    const mine = generation.current
    const question: BotMessage = { id: nextId(), sender: 'user', text }
    setMessages((prev) => [...prev, question])

    // ---------------------------------------------------------------- offline
    if (!online) {
      const grounding = retrieve(text)
      setMessages((prev) => [...prev, {
        id: nextId(),
        sender: 'bot',
        source: 'offline',
        text: tRef.current(grounding.covered ? 'bot.offline.covered' : 'bot.offline.uncovered'),
        rules: grounding.rules,
        citedRules: grounding.rules.map((r) => r.rule_id),
      }])
      return
    }

    // ----------------------------------------------------------------- online
    setBusy(true)
    try {
      const history: ChatTurn[] = [...messages, question]
        .slice(-MAX_HISTORY)
        .map((m) => ({ role: m.sender === 'user' ? 'user' : 'assistant', text: m.text }))
      // The backend requires the last turn to be the fisher's; a conversation
      // trimmed mid-exchange could otherwise start on a bot reply.
      while (history.length > 0 && history[0].role !== 'user') history.shift()

      const res = await api.aiChat(history, language)
      if (generation.current !== mine) return
      setMessages((prev) => [...prev, {
        id: nextId(),
        sender: 'bot',
        text: res.reply,
        source: res.grounded_only ? 'grounded' : 'model',
        citedRules: res.cited_rules,
        disclosures: res.disclosures,
        note: res.controlled_error?.message ?? (res.grounded_only ? res.grounded_label : undefined),
      }])
    } catch {
      if (generation.current !== mine) return
      // The request itself failed (offline mid-send, rate limit, server down).
      // Fall back to the bundled rules rather than leaving the fisher with an
      // error and no answer.
      const grounding = retrieve(text)
      setMessages((prev) => [...prev, {
        id: nextId(),
        sender: 'bot',
        source: 'offline',
        text: tRef.current(grounding.covered ? 'bot.offline.covered' : 'bot.failed'),
        rules: grounding.rules,
        citedRules: grounding.rules.map((r) => r.rule_id),
        failed: true,
      }])
    } finally {
      if (generation.current === mine) setBusy(false)
    }
  }, [busy, language, messages, online])

  return { messages, busy, send, reset }
}
