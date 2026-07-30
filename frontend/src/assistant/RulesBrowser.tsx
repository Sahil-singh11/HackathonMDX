/* Workstream 2 — structured rules browser.
 *
 * Per-species cards from the bundled rules JSON. Everything sourced: rule text,
 * citation, verification status, and scope_note are rendered VERBATIM from the
 * data (honesty rule 4 in CLAUDE.md — never paraphrase a note into something
 * stronger than it says). A species with no verified rule says exactly that;
 * it never shows an invented limit.
 *
 * Layout note: the fact leads, the paperwork follows. A fisher on a boat needs
 * "15 August – 15 October" at a glance; the regulation text, scope caveats and
 * citation are the evidence behind it and sit in a disclosure below. Nothing is
 * removed or softened by that — every character still renders verbatim, one tap
 * away, and anything that changes what the rule MEANS (the mantle-vs-total-
 * length trap, a provisional status, a historical rule) stays on the surface
 * where it cannot be missed.
 */
import {
  AlertTriangle, CalendarOff, ExternalLink, Ruler, ScrollText, Waves,
} from 'lucide-react'
import { Badge, Card } from '../components/ui'
import { useT } from '../i18n'
import {
  OCTOPUS_SPECIES_ID, orderedSpecies, rulesForSpecies,
  sources, type RuleEntry,
} from './rulesData'

/** verification_status → badge tone + label key. Colour is never the only signal. */
function statusBadge(status: string, t: (k: string) => string) {
  switch (status) {
    case 'verified':
    case 'text_verified':
      return <Badge tone="success" icon={<ScrollText size={14} aria-hidden="true" />}>{t('assistant.status.verified')}</Badge>
    case 'provisional':
      return <Badge tone="warning" icon={<AlertTriangle size={14} aria-hidden="true" />}>{t('assistant.status.provisional')}</Badge>
    case 'historical_note':
      return <Badge tone="neutral" icon={<CalendarOff size={14} aria-hidden="true" />}>{t('assistant.status.historical')}</Badge>
    default:
      return <Badge tone="danger" icon={<AlertTriangle size={14} aria-hidden="true" />}>{t('assistant.status.unavailable')}</Badge>
  }
}

/** "08-15" → localised month-day without inventing a year. */
function monthDay(mmdd: string | undefined, locale: string): string {
  if (!mmdd) return ''
  const [m, d] = mmdd.split('-').map(Number)
  // Year 2000 is a leap-year placeholder; only month+day are displayed.
  return new Date(2000, m - 1, d).toLocaleDateString(locale, { day: 'numeric', month: 'long' })
}

/** The headline fact for one rule: a label, an icon, and the value itself. */
function ruleFact(rule: RuleEntry, locale: string, t: (k: string) => string) {
  const isMantle = rule.measurement === 'mantle_length_cm'
  switch (rule.rule_type) {
    case 'seasonal_closure':
      return {
        icon: <CalendarOff size={20} aria-hidden="true" />,
        label: t('assistant.rule.closedSeason'),
        value: `${monthDay(rule.closed_from, locale)} – ${monthDay(rule.closed_to, locale)}`,
        missing: false,
      }
    case 'historical_note':
      return {
        icon: <CalendarOff size={20} aria-hidden="true" />,
        label: t('assistant.rule.historical'),
        value: `${monthDay(rule.closed_from, locale)} – ${monthDay(rule.closed_to, locale)}`,
        missing: false,
      }
    case 'minimum_size':
      return {
        icon: <Ruler size={20} aria-hidden="true" />,
        label: isMantle ? t('assistant.rule.minMantle') : t('assistant.rule.minLength'),
        value: rule.minimum_length_cm != null ? `${rule.minimum_length_cm} cm` : null,
        missing: rule.minimum_length_cm == null,
      }
    default:
      return { icon: <ScrollText size={20} aria-hidden="true" />, label: rule.rule_type, value: null, missing: true }
  }
}

function RuleRow({ rule, locale }: { rule: RuleEntry; locale: string }) {
  const t = useT()
  const isMantle = rule.measurement === 'mantle_length_cm'
  const isHistorical = rule.rule_type === 'historical_note'
  const fact = ruleFact(rule, locale, t)
  const source = sources[rule.source_id]

  return (
    <li className={`asst-rule${isHistorical ? ' asst-rule--muted' : ''}`}>
      <div className="asst-rule__top">
        <span className="asst-rule__icon" aria-hidden="true">{fact.icon}</span>
        <div className="asst-rule__fact">
          <span className="asst-rule__label">{fact.label}</span>
          {fact.value
            ? <strong className="asst-rule__value asst-data">{fact.value}</strong>
            : <span className="asst-rule__value asst-rule__value--missing">
                {t('assistant.rule.noVerifiedRule')}
              </span>}
        </div>
        <span className="asst-rule__status">{statusBadge(rule.verification_status, t)}</span>
      </div>

      {/* Mantle-vs-total-length is the trap in GN 167/2016 — surface it hard.
          This changes what the number MEANS, so it never moves into the
          disclosure below. */}
      {isMantle && (
        <p className="asst-rule__mantle-callout">
          <AlertTriangle size={18} aria-hidden="true" />
          <span>{t('assistant.rule.mantleWarning')}</span>
        </p>
      )}

      {(rule.note || rule.scope_note || rule.rule_id) && (
        <details className="asst-evidence">
          <summary className="asst-evidence__summary">
            <ScrollText size={14} aria-hidden="true" />
            {t('assistant.rule.evidence')}
          </summary>
          <div className="asst-evidence__body">
            {/* Verbatim, per honesty rule 4 — never paraphrased. */}
            {rule.note && <p className="asst-evidence__note">{rule.note}</p>}
            {rule.scope_note && <p className="asst-evidence__scope">{rule.scope_note}</p>}
            <p className="asst-evidence__cite asst-data">
              {rule.rule_id} · {rule.citation ?? rule.source_title}
            </p>
            {source && (
              <a href={source.url} target="_blank" rel="noreferrer" className="asst-evidence__link">
                <span className="asst-data">{rule.source_id}</span>
                <ExternalLink size={14} aria-hidden="true" />
                <span className="sr-only">{t('assistant.opensExternal')}</span>
              </a>
            )}
          </div>
        </details>
      )}
    </li>
  )
}

/** Species-initial avatar. The backend stores no photos, so there is nothing
 *  real to show here — an initial is honest where a stock image would not be. */
function SpeciesMark({ name, highlight }: { name: string; highlight: boolean }) {
  return (
    <span className={`asst-mark${highlight ? ' asst-mark--accent' : ''}`} aria-hidden="true">
      {name.trim().charAt(0).toUpperCase()}
    </span>
  )
}

export default function RulesBrowser() {
  const t = useT()
  // Month names for closure windows: French is the nearest supported locale for
  // Kreol Morisien readers ("15 août" reads naturally; there is no mfe locale).
  const locale = t('assistant.locale')

  return (
    <div className="asst-species-list">
      {orderedSpecies.map((sp) => {
        const speciesRules = rulesForSpecies(sp.species_id)
        const isOctopus = sp.species_id === OCTOPUS_SPECIES_ID
        return (
          <Card key={sp.species_id} raised={isOctopus} className="asst-species">
            <header className="asst-species__head">
              <SpeciesMark name={sp.morisyen} highlight={isOctopus} />
              <div className="asst-species__names">
                {/* h2, not h3: the page h1 is the hero title and Tabs adds no
                    heading of its own, so this is the next level down. */}
                <h2 className="asst-species__title">
                  {sp.morisyen}
                  {sp.morisyen_status !== 'human_verified' && <span aria-hidden="true"> *</span>}
                </h2>
                {/* English name, scientific name and habitat on one line —
                    three separate rows of muted text was most of the bulk. */}
                <p className="asst-species__sub">
                  {sp.english}
                  <span className="asst-species__sci"> · {sp.scientific}</span>
                  <span className="asst-species__habitat">
                    <Waves size={13} aria-hidden="true" />
                    {sp.habitat}
                  </span>
                </p>
              </div>
              {isOctopus && (
                <Badge tone="accent" icon={<ScrollText size={14} aria-hidden="true" />}>
                  {t('assistant.gnBadge')}
                </Badge>
              )}
            </header>

            {speciesRules.length > 0 ? (
              <ul className="asst-rules">
                {speciesRules.map((rule) => <RuleRow key={rule.rule_id} rule={rule} locale={locale} />)}
              </ul>
            ) : (
              <p className="asst-rule__value--missing asst-species__empty">
                {t('assistant.rule.noVerifiedRule')}
              </p>
            )}
          </Card>
        )
      })}
      <p className="asst-footnote">{t('assistant.morisyenPending')}</p>
    </div>
  )
}
