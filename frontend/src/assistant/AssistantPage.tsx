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
 */
import { CloudOff, WifiOff } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { Badge, Tabs } from '../components/ui'
import { useT } from '../i18n'
import { useAnnounce } from '../lib/announce'
import { useOffline } from '../lib/offline'
import AssistantChat from './AssistantChat'
import ModelGate from './ModelGate'
import './assistant.css'
import DeclarationGuide from './DeclarationGuide'
import RulesBrowser from './RulesBrowser'
import { RULES_DISCLAIMER, RULES_VERSION, sources } from './rulesData'

type TabId = 'ask' | 'rules' | 'declaration' | 'sources'

export default function AssistantPage() {
  const t = useT()
  const announce = useAnnounce()
  const { online } = useOffline()
  // Rules is the landing tab, not Ask: the offline-safe reference is the
  // default experience, and the model is opt-in behind a 2 GB download.
  const [tab, setTab] = useState<TabId>('rules')
  const [serverVersion, setServerVersion] = useState<string | null>(null)
  const [model, setModel] = useState<File | null>(null)

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
    { id: 'ask', label: t('assistant.tab.ask') },
    { id: 'rules', label: t('assistant.tab.rules') },
    { id: 'declaration', label: t('assistant.tab.declaration') },
    { id: 'sources', label: t('assistant.tab.sources') },
  ]

  return (
    <div className="lk-scope asst-page">
      <header className="asst-head">
        <h1>{t('assistant.title')}</h1>
        <div className="asst-head__badges">
          {!online && (
            <Badge tone="neutral" icon={<WifiOff size={14} aria-hidden="true" />}>
              {t('assistant.offlineBadge')}
            </Badge>
          )}
          <Badge tone="neutral">
            {t('assistant.rulesVersion')} <span className="asst-data">{RULES_VERSION}</span>
          </Badge>
        </div>
      </header>

      <p className="asst-intro">{t('assistant.intro')}</p>

      {versionMismatch && (
        <p className="asst-stale-warning" role="status">
          <CloudOff size={16} aria-hidden="true" /> {t('assistant.newerRules')}{' '}
          <span className="asst-data">({RULES_VERSION} → {serverVersion})</span>
        </p>
      )}

      <Tabs tabs={tabs} active={tab} onChange={(id) => setTab(id as TabId)}>
        {tab === 'ask' && (
          model
            ? <AssistantChat model={model} onUseRules={() => setTab('rules')} />
            : <ModelGate onReady={setModel} onDecline={() => setTab('rules')} />
        )}
        {tab === 'rules' && <RulesBrowser />}
        {tab === 'declaration' && <DeclarationGuide />}
        {tab === 'sources' && (
          <div className="asst-sources">
            {Object.entries(sources).map(([id, src]) => (
              <div key={id} className="asst-source">
                <h3 className="asst-source__title">
                  <span className="asst-data">{id}</span> · {src.title}
                </h3>
                <p className="asst-source__meta">
                  {src.publisher} · {t('assistant.accessed')}{' '}
                  <span className="asst-data">{src.access_date}</span> ·{' '}
                  <span className="asst-data">{src.verification_status}</span>
                </p>
                {/* Verbatim per honesty rule 4 — this is the register's own wording. */}
                <p className="asst-source__note">{src.note}</p>
                <a href={src.url} target="_blank" rel="noreferrer" className="asst-source__link">
                  {src.url}
                </a>
              </div>
            ))}
          </div>
        )}
      </Tabs>

      {/* The rules file's own disclaimer, verbatim. */}
      <p className="asst-disclaimer">{RULES_DISCLAIMER}</p>
    </div>
  )
}
