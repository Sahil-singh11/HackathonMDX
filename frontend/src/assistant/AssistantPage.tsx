/* Workstream 2 — assistant page (Task 2a: static rules browser).
 *
 * This is the offline-safe foundation the later browser-model work (2b–2d)
 * builds on, and the decline path for users who skip that model download.
 * Everything on this page renders from data bundled at build time; the backend
 * being down changes nothing except the freshness check.
 *
 * Freshness: when online, we revalidate the bundled rules_version against
 * GET /api/rules/static. A mismatch shows a warning that the server has newer
 * rules — we never silently present stale data as current.
 *
 * The "Ask" tab has moved out of this page — the conversational surface is
 * being rebuilt elsewhere. `AssistantChat` and `ModelGate` are untouched and
 * still exported; only this page stopped mounting them, so whoever rebuilds
 * Ask inherits working components rather than a rewrite.
 */
import { CloudOff, WifiOff } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { Badge, Tabs } from '../components/ui'
import { useT } from '../i18n'
import { useAnnounce } from '../lib/announce'
import { useOffline } from '../lib/offline'
import './assistant.css'
import DeclarationGuide from './DeclarationGuide'
import RulesBrowser from './RulesBrowser'
import { RULES_DISCLAIMER, RULES_VERSION, sources } from './rulesData'

type TabId = 'rules' | 'declaration' | 'sources'

export default function AssistantPage() {
  const t = useT()
  const announce = useAnnounce()
  const { online } = useOffline()
  const [tab, setTab] = useState<TabId>('rules')
  const [serverVersion, setServerVersion] = useState<string | null>(null)

  // Revalidate bundled data when online. Failure is fine — offline is expected.
  useEffect(() => {
    if (!online) return
    let stale = false
    api.rulesStatic()
      .then((r) => { if (!stale) setServerVersion(r.rules_version) })
      .catch(() => { /* backend down or old deploy without the endpoint */ })
    return () => { stale = true }
  }, [online])

  const versionMismatch = serverVersion != null && serverVersion !== RULES_VERSION

  useEffect(() => {
    if (versionMismatch) announce(t('assistant.newerRules'))
  }, [versionMismatch, announce, t])

  const tabs = [
    { id: 'rules', label: t('assistant.tab.rules') },
    { id: 'declaration', label: t('assistant.tab.declaration') },
    { id: 'sources', label: t('assistant.tab.sources') },
  ]

  return (
    <div className="lk-scope asst-page">
      {/* The title bar and the tab strip are one unit: this block draws the
          top half of a panel and the tab strip below closes it (see
          `.asst-page > .lk-tabs` in assistant.css). A heading floating free
          above the tabs read as orphaned. The stale-rules warning lives INSIDE
          this block rather than between it and the tabs, so it can appear
          without splitting the panel in two. */}
      <header className="asst-topbar">
        <div className="asst-topbar__row">
          <h1 className="asst-topbar__title">{t('assistant.title')}</h1>
          {!online && (
            <Badge tone="neutral" icon={<WifiOff size={14} aria-hidden="true" />}>
              {t('assistant.offlineBadge')}
            </Badge>
          )}
        </div>

        {/* Says the stored rules are out of date and what to do about it. The
            version numbers themselves are not shown — they are a comparison
            the app makes, not something a fisher acts on. */}
        {versionMismatch && (
          <p className="asst-stale-warning" role="status">
            <CloudOff size={16} aria-hidden="true" /> {t('assistant.newerRules')}
          </p>
        )}
      </header>

      <Tabs tabs={tabs} active={tab} onChange={(id) => setTab(id as TabId)}>
        {tab === 'rules' && <RulesBrowser />}
        {tab === 'declaration' && <DeclarationGuide />}
        {/* One line per source, expandable. The register's publisher, access
            date, verification status, note and URL are all still rendered
            verbatim (honesty rule 4) — collapsing them is what makes the list
            of sources readable at a glance. */}
        {tab === 'sources' && (
          <div className="asst-sources">
            {Object.entries(sources).map(([id, src]) => (
              <details key={id} className="asst-source">
                <summary className="asst-source__summary">
                  <span className="asst-source__id asst-data">{id}</span>
                  <span className="asst-source__title">{src.title}</span>
                </summary>
                <div className="asst-source__body">
                  <p className="asst-source__meta">
                    {src.publisher} · {t('assistant.accessed')}{' '}
                    <span className="asst-data">{src.access_date}</span> ·{' '}
                    <span className="asst-data">{src.verification_status}</span>
                  </p>
                  <p className="asst-source__note">{src.note}</p>
                  <a href={src.url} target="_blank" rel="noreferrer" className="asst-source__link">
                    {src.url}
                  </a>
                </div>
              </details>
            ))}
          </div>
        )}
      </Tabs>

      {/* The rules file's own disclaimer, verbatim. */}
      <p className="asst-disclaimer">{RULES_DISCLAIMER}</p>
    </div>
  )
}
