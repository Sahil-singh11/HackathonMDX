/* Workstream 2 — on-device chat surface (2b engine + 2c grounding).
 *
 * Every question goes through retrieve() first. If the rules data does not
 * cover it, the model is NEVER CALLED — the refusal is deterministic, so there
 * is no generation step in which a regulation could be invented. Covered
 * questions are answered from injected verbatim context, and the answer shows
 * which rule ids grounded it so a fisher can check them in the Rules tab.
 *
 * Props:
 *   model      File   the OPFS-cached model
 *   onUseRules () => void   switch to the rules browser
 */
import { BookMarked, Send, Square } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Button, Card, Spinner } from '../components/ui'
import { useT } from '../i18n'
import { useAnnounce } from '../lib/announce'
import { getEngine, streamReply } from './engine'
import { buildPrompt, retrieve, systemPrompt } from './grounding'
import { useAppStore } from '../store/app'
import type { Conversation } from '@litert-lm/core'

interface Turn {
  role: 'user' | 'model'
  text: string
  /** Set on refusals so the UI can show the rules pointer instead of prose. */
  refused?: boolean
  /** Rule ids that grounded this answer, shown so the fisher can verify. */
  citedRules?: string[]
}

interface Props {
  model: File
  onUseRules: () => void
}

export default function AssistantChat({ model, onUseRules }: Props) {
  const t = useT()
  const announce = useAnnounce()
  const language = useAppStore((s) => s.language)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [errorText, setErrorText] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const conversationRef = useRef<Conversation | null>(null)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const engine = await getEngine(model)
        // The system instruction is the first line of defence against the model
        // reciting a regulation from training; retrieval is the second.
        const conversation = await engine.createConversation({
          preface: { messages: [{ role: 'system', content: systemPrompt(language) }] },
        })
        if (cancelled) { await conversation.delete(); return }
        conversationRef.current = conversation
        setStatus('ready')
      } catch (err) {
        if (cancelled) return
        setErrorText(err instanceof Error ? err.message : String(err))
        setStatus('error')
      }
    })()
    return () => {
      cancelled = true
      void conversationRef.current?.delete()
      conversationRef.current = null
    }
    // Switching language rebuilds the conversation so the system instruction
    // matches; history is short and regenerating is cheaper than a mismatch.
  }, [model, language])

  const send = async () => {
    const question = input.trim()
    const conversation = conversationRef.current
    if (!question || !conversation || busy) return

    setInput('')

    // Fail closed: a question the rules data does not cover never reaches the
    // model, so there is nothing for it to invent an answer from.
    const grounding = retrieve(question)
    if (!grounding.covered) {
      setTurns((prev) => [...prev,
        { role: 'user', text: question },
        { role: 'model', text: t('assistant.chat.outOfScope'), refused: true },
      ])
      announce(t('assistant.chat.outOfScope'))
      return
    }

    setBusy(true)
    setTurns((prev) => [...prev, { role: 'user', text: question }, { role: 'model', text: '' }])

    try {
      await streamReply(conversation, buildPrompt(question, grounding.context), (chunk) => {
        setTurns((prev) => {
          const next = [...prev]
          next[next.length - 1] = { role: 'model', text: next[next.length - 1].text + chunk }
          return next
        })
      })
      setTurns((prev) => {
        const next = [...prev]
        next[next.length - 1] = {
          ...next[next.length - 1],
          citedRules: grounding.rules.map((r) => r.rule_id),
        }
        return next
      })
      announce(t('assistant.chat.a11yAnswered'))
    } catch (err) {
      setTurns((prev) => {
        const next = [...prev]
        next[next.length - 1] = { role: 'model', text: t('assistant.chat.failed') }
        return next
      })
      setErrorText(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  if (status === 'loading') {
    return (
      <Card>
        <Spinner label={t('assistant.chat.loadingModel')} />
        <p className="asst-intro">{t('assistant.chat.loadingNote')}</p>
      </Card>
    )
  }

  if (status === 'error') {
    return (
      <Card title={t('assistant.chat.errorTitle')}>
        <p>{t('assistant.chat.errorBody')}</p>
        <p className="asst-data asst-error-detail">{errorText}</p>
        <Button variant="primary" onClick={onUseRules}>{t('assistant.model.useRules')}</Button>
      </Card>
    )
  }

  return (
    <Card title={t('assistant.chat.title')}>
      {/* Grounded, but still advisory: the rules themselves are largely
          "provisional", and the model is paraphrasing them. */}
      <p className="asst-grounded-note" role="note">
        <BookMarked size={16} aria-hidden="true" />
        {t('assistant.chat.groundedNote')}
      </p>

      <div className="asst-turns" role="log" aria-label={t('assistant.chat.title')}>
        {turns.length === 0 && (
          <>
            <p className="asst-intro">{t('assistant.chat.emptyHint')}</p>
            <ul className="asst-scope-list">
              <li>{t('assistant.chat.scopeSize')}</li>
              <li>{t('assistant.chat.scopeSeason')}</li>
              <li>{t('assistant.chat.scopeDeclaration')}</li>
            </ul>
          </>
        )}
        {turns.map((turn, i) => (
          <div key={i} className={`asst-turn asst-turn--${turn.role}`}>
            <span className="asst-turn__role">
              {t(turn.role === 'user' ? 'assistant.chat.you' : 'assistant.chat.model')}
            </span>
            <p>{turn.text || (busy && i === turns.length - 1 ? '…' : '')}</p>
            {turn.refused && (
              <Button variant="secondary" onClick={onUseRules}>{t('assistant.model.useRules')}</Button>
            )}
            {turn.citedRules && turn.citedRules.length > 0 && (
              <p className="asst-citations asst-data">
                {t('assistant.chat.basedOn')} {turn.citedRules.join(', ')}
              </p>
            )}
          </div>
        ))}
      </div>

      <form className="asst-composer" onSubmit={(e) => { e.preventDefault(); void send() }}>
        <label className="sr-only" htmlFor="asst-input">{t('assistant.chat.inputLabel')}</label>
        <input id="asst-input" value={input} onChange={(e) => setInput(e.target.value)}
          placeholder={t('assistant.chat.placeholder')} disabled={busy} autoComplete="off" />
        {busy ? (
          <Button variant="secondary" type="button"
            icon={<Square size={16} aria-hidden="true" />}
            onClick={() => conversationRef.current?.cancel()}>
            {t('assistant.chat.stop')}
          </Button>
        ) : (
          <Button variant="primary" type="submit" disabled={!input.trim()}
            icon={<Send size={16} aria-hidden="true" />}>
            {t('assistant.chat.send')}
          </Button>
        )}
      </form>

      <p className="asst-intro">{t('assistant.chat.rulesPointer')}</p>
    </Card>
  )
}
