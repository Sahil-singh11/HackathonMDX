/**
 * The rules behind an offline answer, rendered as facts.
 *
 * Same data, same i18n keys and same status vocabulary as the Fishing rules
 * page (assistant/RulesBrowser) — condensed to what fits in a chat bubble, and
 * still never paraphrased. If a rule is provisional it says provisional here
 * too; if there is no verified minimum it says that rather than showing a
 * number from a neighbouring rule.
 */
import { AlertTriangle, CalendarOff, Ruler, ScrollText } from 'lucide-react'
import { Badge } from '../ui'
import { useT } from '../../i18n'
import { species, type RuleEntry } from '../../assistant/rulesData'

function speciesLabel(speciesId: string): string {
  const sp = species.find((s) => s.species_id === speciesId)
  return sp ? `${sp.morisyen} — ${sp.english}` : speciesId
}

/** "08-15" → localised month-day. No year is invented; only month and day exist in the data. */
function monthDay(mmdd: string | undefined, locale: string): string {
  if (!mmdd) return ''
  const [m, d] = mmdd.split('-').map(Number)
  return new Date(2000, m - 1, d).toLocaleDateString(locale, { day: 'numeric', month: 'long' })
}

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

export function BotRuleFacts({ rules }: { rules: RuleEntry[] }) {
  const t = useT()
  const locale = t('assistant.locale')

  return (
    <ul className="lkbot-facts">
      {rules.map((rule) => {
        const isMantle = rule.measurement === 'mantle_length_cm'
        return (
          <li key={rule.rule_id} className="lkbot-fact">
            <p className="lkbot-fact__species">{speciesLabel(rule.species_id)}</p>

            {rule.rule_type === 'seasonal_closure' && (
              <p className="lkbot-fact__line">
                <CalendarOff size={16} aria-hidden="true" />
                <span><strong>{t('assistant.rule.closedSeason')}:</strong>{' '}
                  <span className="lkbot-data">
                    {monthDay(rule.closed_from, locale)} – {monthDay(rule.closed_to, locale)}
                  </span>
                </span>
              </p>
            )}

            {rule.rule_type === 'historical_note' && (
              <p className="lkbot-fact__line">
                <CalendarOff size={16} aria-hidden="true" />
                <span><strong>{t('assistant.rule.historical')}:</strong>{' '}
                  <span className="lkbot-data">
                    {monthDay(rule.closed_from, locale)} – {monthDay(rule.closed_to, locale)}
                  </span>
                </span>
              </p>
            )}

            {rule.rule_type === 'minimum_size' && (
              <p className="lkbot-fact__line">
                <Ruler size={16} aria-hidden="true" />
                {rule.minimum_length_cm != null ? (
                  <span>
                    <strong>{isMantle ? t('assistant.rule.minMantle') : t('assistant.rule.minLength')}:</strong>{' '}
                    <span className="lkbot-data">{rule.minimum_length_cm} cm</span>
                  </span>
                ) : (
                  <span>
                    <strong>{t('assistant.rule.minLength')}:</strong> {t('assistant.rule.noVerifiedRule')}
                  </span>
                )}
              </p>
            )}

            {/* Mantle-vs-total-length is the trap in GN 167/2016. It decides
                whether a fisher keeps a legal catch, so it is never collapsed
                into the line above. */}
            {isMantle && (
              <p className="lkbot-fact__warn">
                <AlertTriangle size={15} aria-hidden="true" /> {t('assistant.rule.mantleWarning')}
              </p>
            )}

            <p className="lkbot-fact__cite">
              {statusBadge(rule.verification_status, t)}
              <span className="lkbot-data">{rule.rule_id}</span>
            </p>
          </li>
        )
      })}
    </ul>
  )
}
