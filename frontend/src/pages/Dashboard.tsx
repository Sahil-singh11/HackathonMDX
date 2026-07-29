import { useQuery } from '@tanstack/react-query'
import {
  Anchor, BookOpen, Camera, CloudOff, Info, ShieldCheck,
  SlidersHorizontal, Waves, Wrench,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useT } from '../i18n'
import { useAppStore } from '../store/app'

export default function Dashboard() {
  const t = useT()
  const profileName = useAppStore((s) => s.profileName)
  const { data: report } = useQuery({ queryKey: ['reportToday'], queryFn: api.reportToday })
  const { data: queue } = useQuery({ queryKey: ['syncQueue'], queryFn: api.syncQueue })

  const tiles = [
    { to: '/catch', icon: <Camera className="icon" aria-hidden="true" />, label: t('nav.catch'), coral: true },
    { to: '/marine', icon: <Waves className="icon" aria-hidden="true" />, label: t('nav.marine') },
    { to: '/history', icon: <BookOpen className="icon" aria-hidden="true" />, label: t('nav.history') },
    { to: '/declaration', icon: <Anchor className="icon" aria-hidden="true" />, label: t('nav.declaration') },
    { to: '/queue', icon: <CloudOff className="icon" aria-hidden="true" />, label: `${t('nav.queue')}${queue?.queued ? ` (${queue.queued})` : ''}` },
    { to: '/proof', icon: <Wrench className="icon" aria-hidden="true" />, label: t('nav.proof') },
    { to: '/demo', icon: <SlidersHorizontal className="icon" aria-hidden="true" />, label: t('nav.demo') },
    { to: '/privacy', icon: <ShieldCheck className="icon" aria-hidden="true" />, label: t('nav.privacy') },
    { to: '/about', icon: <Info className="icon" aria-hidden="true" />, label: t('nav.about') },
  ]

  return (
    <>
      <div className="card">
        <h2>{profileName ? `${t('landing.welcome')}, ${profileName}` : t('landing.welcome')}</h2>
        <div className="stat-grid">
          <div className="stat">
            <div className="label">{t('history.today')}</div>
            <div className="value">{String(report?.total_count ?? 0)}<span className="unit">{t('history.total')}</span></div>
          </div>
          <div className="stat">
            <div className="label">{t('queue.queued')}</div>
            <div className="value">{queue?.queued ?? 0}</div>
          </div>
        </div>
      </div>
      <div className="grid">
        {tiles.map((x) => (
          <Link key={x.to} to={x.to} className={`tile${x.coral ? ' coral' : ''}`}>
            {x.icon}<strong>{x.label}</strong>
          </Link>
        ))}
      </div>
      <p className="banner info">{t('limitation.permanent')}</p>
    </>
  )
}
