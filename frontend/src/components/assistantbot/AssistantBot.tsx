/**
 * Floating assistant — the logo button in the bottom-right corner and the chat
 * panel it opens.
 *
 * WHY IT LOOKS RESTRAINED. This is a surface a ministry officer will be shown.
 * A chat window on a government-facing tool is only defensible if a reader can
 * tell, per message, where the answer came from — so every bot turn carries a
 * provenance chip (hosted model / rules data / offline) and every rule-backed
 * answer carries the rule ids it used. Nothing here says "AI" as a badge of
 * quality; it says which of three concrete things produced the sentence.
 *
 * ACCESSIBILITY. Behaves as a modal dialog at every width: focus moves in on
 * open, Tab is trapped, Escape closes, focus returns to the launcher. That
 * matches the frozen `Sheet` primitive's contract — the behaviour is
 * reimplemented rather than reused only because Sheet is a centred modal and
 * this is a corner-docked panel, and `components/ui` is read-only.
 *
 * The launcher is never icon-only: the mark is paired with a visible label at
 * every breakpoint, and both sit inside one 56px (64px in Sunlight) target.
 */
import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { BookMarked, CloudOff, Cpu, RotateCcw, Send, X } from 'lucide-react'
import { useT } from '../../i18n'
import { useAnnounce } from '../../lib/announce'
import { useOffline } from '../../lib/offline'
import { useAppStore } from '../../store/app'
import { BotRuleFacts } from './BotRuleFacts'
import { useBotChat, type AnswerSource, type BotMessage } from './useBotChat'
import './assistantbot.css'

const FOCUSABLE = [
  'a[href]', 'button:not([disabled])', 'input:not([disabled])', 'select:not([disabled])',
  'textarea:not([disabled])', '[tabindex]:not([tabindex="-1"])',
].join(',')

const SOURCE_ICON: Record<AnswerSource, typeof Cpu> = {
  model: Cpu,
  grounded: BookMarked,
  offline: CloudOff,
}

/** Where this answer came from. Text as well as icon — colour is never the only signal. */
function SourceChip({ source }: { source: AnswerSource }) {
  const t = useT()
  const Icon = SOURCE_ICON[source]
  return (
    <span className={`lkbot-chip lkbot-chip--${source}`}>
      <Icon size={14} aria-hidden="true" />
      {t(`bot.source.${source}`)}
    </span>
  )
}

function BotTurn({ message }: { message: BotMessage }) {
  const t = useT()
  const isUser = message.sender === 'user'

  return (
    <div className={`lkbot-turn lkbot-turn--${isUser ? 'user' : 'bot'}`}>
      <span className="lk-sr-only">{t(isUser ? 'bot.you' : 'bot.assistant')}</span>
      <div className="lkbot-bubble">
        {!isUser && message.source && <SourceChip source={message.source} />}
        <p className="lkbot-bubble__text">{message.text}</p>

        {message.rules && message.rules.length > 0 && <BotRuleFacts rules={message.rules} />}

        {!message.rules?.length && message.citedRules && message.citedRules.length > 0 && (
          <p className="lkbot-cited">
            {t('bot.basedOn')} <span className="lkbot-data">{message.citedRules.join(', ')}</span>
          </p>
        )}

        {message.note && <p className="lkbot-note">{message.note}</p>}

        {!isUser && (
          <Link className="lkbot-rules-link" to="/assistant">{t('bot.openRules')}</Link>
        )}
      </div>
    </div>
  )
}

export default function AssistantBot() {
  const t = useT()
  const announce = useAnnounce()
  const { online } = useOffline()
  const language = useAppStore((s) => s.language)

  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const panelRef = useRef<HTMLDivElement>(null)
  const launcherRef = useRef<HTMLButtonElement>(null)
  const logRef = useRef<HTMLDivElement>(null)
  const titleId = useId()
  const panelId = useId()

  const { messages, busy, send, reset } = useBotChat(language, online)

  const close = useCallback(() => {
    setOpen(false)
    // After the panel unmounts, put focus back where it came from.
    window.setTimeout(() => launcherRef.current?.focus(), 0)
  }, [])

  // Focus in, Tab trapped, Escape closes.
  useEffect(() => {
    if (!open) return
    const first = panelRef.current?.querySelector<HTMLElement>('input, textarea')
    ;(first ?? panelRef.current)?.focus()

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); close(); return }
      if (e.key !== 'Tab') return
      const nodes = panelRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE)
      if (!nodes || nodes.length === 0) return
      const list = Array.from(nodes)
      const firstEl = list[0]
      const lastEl = list[list.length - 1]
      if (e.shiftKey && document.activeElement === firstEl) { e.preventDefault(); lastEl.focus() }
      else if (!e.shiftKey && document.activeElement === lastEl) { e.preventDefault(); firstEl.focus() }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open, close])

  // Keep the newest turn in view. `block: 'nearest'` scrolls the log, not the page.
  useEffect(() => {
    if (!open) return
    logRef.current?.lastElementChild?.scrollIntoView({ block: 'nearest' })
  }, [messages, open])

  // Announce the OUTCOME only — not that a request started.
  const lastId = messages[messages.length - 1]?.id
  const announcedRef = useRef<string | undefined>(undefined)
  useEffect(() => {
    const last = messages[messages.length - 1]
    if (!last || last.sender !== 'bot' || announcedRef.current === last.id) return
    announcedRef.current = last.id
    announce(t('bot.a11y.answered'))
  }, [lastId, messages, announce, t])

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const text = draft
    setDraft('')
    void send(text)
  }

  const suggestions = [t('bot.suggest.size'), t('bot.suggest.season'), t('bot.suggest.declaration')]

  return (
    <>
      <button
        ref={launcherRef}
        type="button"
        className="lkbot-launcher lk-scope"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => (open ? close() : setOpen(true))}
      >
        <img className="lkbot-launcher__mark" src="/assistant-logo.svg" alt="" aria-hidden="true" />
        <span className="lkbot-launcher__label">{t('bot.launch')}</span>
      </button>

      {open && (
        <div className="lkbot-scrim" onMouseDown={(e) => { if (e.target === e.currentTarget) close() }}>
          <div
            id={panelId}
            className="lkbot-panel lk-scope"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            ref={panelRef}
            tabIndex={-1}
          >
            <header className="lkbot-header">
              <img className="lkbot-header__mark" src="/assistant-logo.svg" alt="" aria-hidden="true" />
              <div className="lkbot-header__text">
                <h2 id={titleId}>{t('bot.title')}</h2>
                <p>{online ? t('bot.subtitle.online') : t('bot.subtitle.offline')}</p>
              </div>
              {messages.length > 0 && (
                <button type="button" className="lkbot-header__btn" onClick={reset}>
                  <RotateCcw size={18} aria-hidden="true" />
                  <span className="lk-sr-only">{t('bot.clear')}</span>
                </button>
              )}
              <button type="button" className="lkbot-header__btn" onClick={close}>
                <X size={20} aria-hidden="true" />
                <span className="lk-sr-only">{t('bot.close')}</span>
              </button>
            </header>

            <div className="lkbot-log" role="log" aria-label={t('bot.title')} ref={logRef}>
              {messages.length === 0 && (
                <div className="lkbot-intro">
                  <p>{t('bot.intro')}</p>
                  <p className="lkbot-scope">{t('bot.scope')}</p>
                  <ul className="lkbot-suggestions">
                    {suggestions.map((s) => (
                      <li key={s}>
                        <button type="button" className="lkbot-suggestion"
                          onClick={() => void send(s)}>{s}</button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {messages.map((m) => <BotTurn key={m.id} message={m} />)}

              {busy && (
                <div className="lkbot-turn lkbot-turn--bot">
                  <div className="lkbot-bubble lkbot-bubble--pending">
                    <span className="lkbot-dots" aria-hidden="true"><i /><i /><i /></span>
                    {t('bot.thinking')}
                  </div>
                </div>
              )}
            </div>

            <form className="lkbot-composer" onSubmit={submit}>
              <label className="lk-sr-only" htmlFor="lkbot-input">{t('bot.inputLabel')}</label>
              <input
                id="lkbot-input"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder={t('bot.placeholder')}
                autoComplete="off"
                maxLength={1000}
                disabled={busy}
              />
              <button type="submit" className="lkbot-send" disabled={busy || !draft.trim()}>
                <Send size={18} aria-hidden="true" />
                <span>{t('bot.send')}</span>
              </button>
            </form>

            <p className="lkbot-footer">{t('bot.disclaimer')}</p>
          </div>
        </div>
      )}
    </>
  )
}
