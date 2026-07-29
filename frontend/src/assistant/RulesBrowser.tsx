/* Workstream 2 — structured rules browser.
 *
 * Per-species cards from the bundled rules JSON. Everything sourced: rule text,
 * citation, verification status, and scope_note are rendered VERBATIM from the
 * data (honesty rule 4 in CLAUDE.md — never paraphrase a note into something
 * stronger than it says). A species with no verified rule says exactly that;
 * it never shows an invented limit.
 */
import { AlertTriangle, CalendarOff, ExternalLink, Ruler, ScrollText } from 'lucide-react'
import { Badge, Card, Divider } from '../components/ui'
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

function RuleRow({ rule, locale }: { rule: RuleEntry; locale: string }) {
  const t = useT()
  const isMantle = rule.measurement === 'mantle_length_cm'

  return (
    <div className="asst-rule">
      <div className="asst-rule__head">
        {rule.rule_type === 'seasonal_closure' && (
          <span className="asst-rule__fact">
            <CalendarOff size={18} aria-hidden="true" />
            <strong>{t('assistant.rule.closedSeason')}:</strong>{' '}
            <span className="asst-data">
              {monthDay(rule.closed_from, locale)} – {monthDay(rule.closed_to, locale)}
            </span>
          </span>
        )}
        {rule.rule_type === 'minimum_size' && rule.minimum_length_cm != null && (
          <span className="asst-rule__fact">
            <Ruler size={18} aria-hidden="true" />
            <strong>{isMantle ? t('assistant.rule.minMantle') : t('assistant.rule.minLength')}:</strong>{' '}
            <span className="asst-data">{rule.minimum_length_cm} cm</span>
          </span>
        )}
        {rule.rule_type === 'minimum_size' && rule.minimum_length_cm == null && (
          <span className="asst-rule__fact">
            <Ruler size={18} aria-hidden="true" />
            <strong>{t('assistant.rule.minLength')}:</strong> {t('assistant.rule.noVerifiedRule')}
          </span>
        )}
        {rule.rule_type === 'historical_note' && (
          <span className="asst-rule__fact">
            <CalendarOff size={18} aria-hidden="true" />
            <strong>{t('assistant.rule.historical')}:</strong>{' '}
            <span className="asst-data">
              {monthDay(rule.closed_from, locale)} – {monthDay(rule.closed_to, locale)}
            </span>
          </span>
        )}
        {statusBadge(rule.verification_status, t)}
      </div>

      {/* Mantle-vs-total-length is the trap in GN 167/2016 — surface it hard. */}
      {isMantle && (
        <p className="asst-rule__mantle-callout">
          <AlertTriangle size={16} aria-hidden="true" /> {t('assistant.rule.mantleWarning')}
        </p>
      )}

      {rule.note && <p className="asst-rule__note">{rule.note}</p>}
      {rule.scope_note && <p className="asst-rule__scope">{rule.scope_note}</p>}

      <p className="asst-rule__cite asst-data">
        {rule.rule_id} · {rule.citation ?? rule.source_title}
        {sources[rule.source_id] && (
          <>
            {' · '}
            <a href={sources[rule.source_id].url} target="_blank" rel="noreferrer">
              {rule.source_id} <ExternalLink size={12} aria-hidden="true" />
              <span className="sr-only">{t('assistant.opensExternal')}</span>
            </a>
          </>
        )}
      </p>
    </div>
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
          <Card
            key={sp.species_id}
            raised={isOctopus}
            title={
              <span className="asst-species-title">
                {sp.morisyen}
                {sp.morisyen_status !== 'human_verified' && <span aria-hidden="true"> *</span>}
                {' — '}{sp.english}
                <span className="asst-species-sci"> ({sp.scientific})</span>
              </span>
            }
            action={isOctopus
              ? <Badge tone="accent" icon={<ScrollText size={14} aria-hidden="true" />}>{t('assistant.gnBadge')}</Badge>
              : undefined}
          >
            <p className="asst-habitat">{sp.habitat}</p>
            <Divider tight />
            {speciesRules.length > 0
              ? speciesRules.map((rule) => <RuleRow key={rule.rule_id} rule={rule} locale={locale} />)
              : <p className="asst-rule__note">{t('assistant.rule.noVerifiedRule')}</p>}
          </Card>
        )
      })}
      <p className="asst-footnote">{t('assistant.morisyenPending')}</p>
    </div>
  )
}
