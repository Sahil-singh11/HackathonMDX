/**
 * Floating assistant — the logo button in the bottom-right corner and the chat
 * panel it opens.
 *
 * WHY IT LOOKS RESTRAINED. This is a surface a ministry officer will be shown.
 * A chat window on a government-facing tool is only defensible if a reader can
 * tell, per message, where the answer came from — so every bot turn carries a
 * provenance badge (the frozen ui/Badge, same one every other page uses for
 * status: hosted model / rules data / offline) and every rule-backed answer
 * carries the rule ids it used. Nothing here says "AI" as a badge of quality;
 * it says which of three concrete things produced the sentence. The panel's
 * only ornament is a 3px accent bar under the header — closer to a letterhead
 * than a chat-product flourish — and the launcher's presence dot is neutral,
 * not red, when offline: offline is this app's expected state, not a fault.
 *
 * ACCESSIBILITY. Behaves as a modal dialog at every width: focus moves in on
 * open, Tab is trapped, Escape closes, focus returns to the launcher. That
 * matches the frozen `Sheet` primitive's contract — the behaviour is
 * reimplemented rather than reused only because Sheet is a centred modal and
 * this is a corner-docked panel, and `components/ui` is read-only.
 *
 * The launcher is never icon-only: mark-plus-label when closed, X-plus-label
 * when open, and both states sit inside one 56px (64px in Sunlight) target.
 */
import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Anchor, BookMarked, CalendarOff, CloudOff, Cpu, Ruler, RotateCcw, Send, X,
} from 'lucide-react'
import { Badge, type BadgeTone } from '../ui'
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

/** Icon AND tone AND text all carry the distinction — never colour alone. */
const SOURCE_META: Record<AnswerSource, { icon: typeof Cpu; tone: BadgeTone }> = {
  model: { icon: Cpu, tone: 'accent' },
  grounded: { icon: BookMarked, tone: 'neutral' },
  offline: { icon: CloudOff, tone: 'neutral' },
}

/** Where this answer came from, using the same frozen Badge every other page
 *  uses for status — so provenance reads as a fact of the app, not a chat
 *  affectation. */
function SourceChip({ source }: { source: AnswerSource }) {
  const t = useT()
  const { icon: Icon, tone } = SOURCE_META[source]
  return (
    <Badge tone={tone} icon={<Icon size={13} aria-hidden="true" />}>
      {t(`bot.source.${source}`)}
    </Badge>
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

/** Remembers a dismissal for the rest of the browser session, so the greeting
 *  happens once and a fisher who closed it is not greeted again on every
 *  return to Home. sessionStorage (not local) so a new visit greets afresh. */
const GREETED_KEY = 'lk-nemo-greeted'

function alreadyGreeted(): boolean {
  try {
    return window.sessionStorage.getItem(GREETED_KEY) === '1'
  } catch {
    return false // Storage blocked (private mode) — greet, do not crash.
  }
}

function markGreeted(): void {
  try {
    window.sessionStorage.setItem(GREETED_KEY, '1')
  } catch {
    /* ignore */
  }
}

/**
 * @param autoOpen  greet on arrival instead of waiting to be clicked. Only
 *                  Home passes this. An auto-opened panel is deliberately
 *                  NON-MODAL — see the modality note below.
 */
export default function AssistantBot({ autoOpen = false }: { autoOpen?: boolean }) {
  const t = useT()
  const announce = useAnnounce()
  const { online } = useOffline()
  const language = useAppStore((s) => s.language)

  const [open, setOpen] = useState(false)
  /**
   * MODALITY IS EARNED, NOT ASSUMED.
   *
   * A panel the fisher opened is modal: focus moves in, Tab is trapped, a
   * scrim dims the page. That is right, because they asked for it.
   *
   * A panel that opened ITSELF must not do any of that. Auto-trapping focus
   * would drop a keyboard or screen-reader user into a chat box before they
   * ever reached the page they navigated to, which fails the accessibility
   * floor outright. So a greeting is non-modal: no scrim, no focus trap, no
   * stolen focus. It sits in the corner and waits. Escape still closes it, and
   * the moment the fisher clicks into it they are simply using a normal panel.
   */
  const [modal, setModal] = useState(false)
  const [draft, setDraft] = useState('')
  const panelRef = useRef<HTMLDivElement>(null)
  const launcherRef = useRef<HTMLButtonElement>(null)
  const logRef = useRef<HTMLDivElement>(null)
  const titleId = useId()
  const panelId = useId()

  const { messages, busy, send, reset } = useBotChat(language, online)

  const close = useCallback(() => {
    // Read before clearing: focus is only restored if we had taken it. A
    // greeting never moved focus, so returning it on close would yank the
    // fisher out of whatever they were actually doing.
    const hadFocus = modal
    setOpen(false)
    setModal(false)
    markGreeted()
    if (hadFocus) window.setTimeout(() => launcherRef.current?.focus(), 0)
  }, [modal])

  const openModal = useCallback(() => {
    setOpen(true)
    setModal(true)
    markGreeted()
  }, [])

  // The greeting. Once per session, Home only, and never on a phone: a fisher
  // opening the app on deck to record a catch must not have to dismiss a chat
  // panel covering the screen first. On a phone the panel is a full-width
  // bottom sheet, so "non-modal" would not save them from that.
  useEffect(() => {
    if (!autoOpen || alreadyGreeted()) return
    if (window.matchMedia('(max-width: 767px)').matches) return
    const timer = window.setTimeout(() => {
      setOpen(true)
      setModal(false)
      markGreeted()
    }, 1200)
    return () => window.clearTimeout(timer)
  }, [autoOpen])

  // Focus in, Tab trapped, Escape closes — modal panels only.
  useEffect(() => {
    if (!open) return

    if (modal) {
      const first = panelRef.current?.querySelector<HTMLElement>('input, textarea')
      ;(first ?? panelRef.current)?.focus()
    }

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); close(); return }
      if (e.key !== 'Tab' || !modal) return
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
  }, [open, modal, close])

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

  // Icon paired with each suggestion so the row scans at a glance rather than
  // reading as an undifferentiated list of sentences.
  const suggestions = [
    { icon: Ruler, text: t('bot.suggest.size') },
    { icon: CalendarOff, text: t('bot.suggest.season') },
    { icon: Anchor, text: t('bot.suggest.declaration') },
  ]

  return (
    <>
      <button
        ref={launcherRef}
        type="button"
        className={`lkbot-launcher lk-scope${open ? ' lkbot-launcher--open' : ''}`}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => (open ? close() : openModal())}
      >
        {open ? (
          <span className="lkbot-launcher__icon"><X size={22} aria-hidden="true" /></span>
        ) : (
          <span className="lkbot-launcher__mark-wrap">
            <img className="lkbot-launcher__mark" src="/assistant-logo.svg" alt="" aria-hidden="true" />
            <span className={`lkbot-status-dot${online ? ' lkbot-status-dot--online' : ''}`} aria-hidden="true" />
          </span>
        )}
        <span className="lkbot-launcher__label">{t(open ? 'bot.close' : 'bot.launch')}</span>
      </button>

      {open && (
        <div
          className={`lkbot-scrim${modal ? '' : ' lkbot-scrim--quiet'}`}
          onMouseDown={(e) => { if (modal && e.target === e.currentTarget) close() }}
        >
          <div
            id={panelId}
            className="lkbot-panel lk-scope"
            role="dialog"
            aria-modal={modal || undefined}
            aria-labelledby={titleId}
            ref={panelRef}
            tabIndex={-1}
            // A greeting the fisher engages with stops being a greeting. From
            // the first click inside, it behaves like any panel they opened.
            onMouseDown={() => { if (!modal) setModal(true) }}
          >
            <header className="lkbot-header">
              <span className="lkbot-header__mark-wrap">
                <img className="lkbot-header__mark" src="/assistant-logo.svg" alt="" aria-hidden="true" />
                <span className={`lkbot-status-dot${online ? ' lkbot-status-dot--online' : ''}`} aria-hidden="true" />
              </span>
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
                    {suggestions.map(({ icon: Icon, text }) => (
                      <li key={text}>
                        <button type="button" className="lkbot-suggestion"
                          onClick={() => void send(text)}>
                          <Icon size={16} aria-hidden="true" />
                          {text}
                        </button>
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
