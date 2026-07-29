/* Workstream 2 — on-device chat surface.
 *
 * Task 2b scope: get a model loaded and streaming in the browser. GROUNDING IS
 * NOT IMPLEMENTED YET (that is Task 2c). Until it is, this component must not
 * present answers as authoritative regulation: the banner says every answer is
 * unverified and points at the rules browser, and the placeholder does not
 * invite regulatory questions. Removing that banner is part of 2c, not before.
 *
 * Props:
 *   model      File   the OPFS-cached model
 *   onUseRules () => void   switch to the rules browser
 */
import { AlertTriangle, Send, Square } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Button, Card, Spinner } from '../components/ui'
import { useT } from '../i18n'
import { useAnnounce } from '../lib/announce'
import { getEngine, streamReply } from './engine'
import type { Conversation } from '@litert-lm/core'

interface Turn {
  role: 'user' | 'model'
  text: string
}

interface Props {
  model: File
  onUseRules: () => void
}

export default function AssistantChat({ model, onUseRules }: Props) {
  const t = useT()
  const announce = useAnnounce()
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
        const conversation = await engine.createConversation()
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
  }, [model])

  const send = async () => {
    const question = input.trim()
    const conversation = conversationRef.current
    if (!question || !conversation || busy) return

    setInput('')
    setBusy(true)
    setTurns((prev) => [...prev, { role: 'user', text: question }, { role: 'model', text: '' }])

    try {
      await streamReply(conversation, question, (chunk) => {
        setTurns((prev) => {
          const next = [...prev]
          next[next.length - 1] = { role: 'model', text: next[next.length - 1].text + chunk }
          return next
        })
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
      {/* Removed only when Task 2c lands grounding. */}
      <p className="asst-ungrounded-warning" role="note">
        <AlertTriangle size={16} aria-hidden="true" />
        {t('assistant.chat.ungroundedWarning')}
      </p>

      <div className="asst-turns" role="log" aria-label={t('assistant.chat.title')}>
        {turns.length === 0 && <p className="asst-intro">{t('assistant.chat.emptyHint')}</p>}
        {turns.map((turn, i) => (
          <div key={i} className={`asst-turn asst-turn--${turn.role}`}>
            <span className="asst-turn__role">
              {t(turn.role === 'user' ? 'assistant.chat.you' : 'assistant.chat.model')}
            </span>
            <p>{turn.text || (busy && i === turns.length - 1 ? '…' : '')}</p>
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
