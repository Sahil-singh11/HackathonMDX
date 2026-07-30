import { useQuery } from '@tanstack/react-query'
import {
  Anchor, BookOpen, Calendar, Camera, CloudOff, Compass, Fish, Info, Scale,
  ShieldCheck, SlidersHorizontal, Thermometer, Waves, Wrench,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type SpeciesCandidate } from '../api/client'
import AssistantBot from '../components/assistantbot/AssistantBot'
import { useT } from '../i18n'
import { useAppStore } from '../store/app'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function formatNiceDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  if (!y || !m || !d) return iso
  return `${d} ${MONTHS[m - 1]} ${y}`
}

function formatRelativeActivity(createdAt: string | undefined, t: (k: string) => string): string {
  if (!createdAt) return ''
  const then = new Date(createdAt)
  if (Number.isNaN(then.getTime())) return createdAt
  const diffMs = Date.now() - then.getTime()
  if (diffMs < 3_600_000) return t('dashboard.justNow')
  const now = new Date()
  if (then.toDateString() === now.toDateString()) return t('dashboard.today')
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  if (then.toDateString() === yesterday.toDateString()) return t('dashboard.yesterday')
  return formatNiceDate(then.toISOString().slice(0, 10))
}

function useCountUp(target: number, duration = 600): number {
  const [value, setValue] = useState(0)
  useEffect(() => {
    const reduceMotion = typeof window !== 'undefined'
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduceMotion) { setValue(target); return }
    let raf = 0
    const start = performance.now()
    const step = (now: number) => {
      const progress = Math.min(1, (now - start) / duration)
      setValue(target * progress)
      if (progress < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [target, duration])
  return value
}

const AVATAR_HUES = ['avatar-hue-0', 'avatar-hue-1', 'avatar-hue-2']

function Avatar({ label, index, size }: { label: string; index: number; size?: 'lg' }) {
  return (
    <span className={`avatar-circle ${AVATAR_HUES[index % AVATAR_HUES.length]}${size ? ` ${size}` : ''}`} aria-hidden="true">
      {label.slice(0, 2).toUpperCase()}
    </span>
  )
}

export default function Dashboard() {
  const t = useT()
  const profileName = useAppStore((s) => s.profileName)
  const { data: config } = useQuery({ queryKey: ['config'], queryFn: api.config })
  const { data: report } = useQuery({ queryKey: ['reportToday'], queryFn: api.reportToday })
  const { data: queue } = useQuery({ queryKey: ['syncQueue'], queryFn: api.syncQueue })
  const { data: catchesData } = useQuery({ queryKey: ['catches'], queryFn: api.catches })
  const { data: marine } = useQuery({ queryKey: ['marine'], queryFn: api.marine })
  const { data: speciesData } = useQuery({ queryKey: ['species'], queryFn: api.species })

  const catches = catchesData?.catches ?? []
  const todayCount = Number(report?.total_count ?? 0)
  const queuedCount = Number(queue?.queued ?? 0)
  const waveHeight = typeof marine?.wave_height_m === 'number' ? marine.wave_height_m as number : null
  const seaTemp = typeof marine?.sea_surface_temperature_c === 'number' ? marine.sea_surface_temperature_c as number : null
  const lastTripDate = catches[0]?.capture_date as string | undefined
  const distinctSpecies = new Set(catches.map((c) => c.species_id)).size

  const todayAnimated = useCountUp(todayCount)
  const queuedAnimated = useCountUp(queuedCount)
  const seaTempAnimated = useCountUp(seaTemp ?? 0)

  const speciesById = new Map<string, SpeciesCandidate>((speciesData?.species ?? []).map((s) => [s.species_id, s]))
  const speciesLabel = (id: string) => speciesById.get(id)?.english ?? id

  const heroDate = formatNiceDate(config?.current_date ?? new Date().toISOString().slice(0, 10))
  const recentThree = catches.slice(0, 3)

  // /assistant and /pillars lead deliberately: they are features, not utility
  // pages, and this grid is the only way to reach either one on a phone (the
  // tab bar is full at five, and seven targets would break the 56px touch
  // floor at 360px). Desktop also surfaces them in the side nav. See the
  // secondaryNavItems comment in components/shell.
  const toolButtons = [
    { to: '/assistant', icon: Scale, label: t('assistant.title') },
    { to: '/pillars', icon: Compass, label: t('pillars.title') },
    { to: '/queue', icon: CloudOff, label: t('nav.queue'), badge: queuedCount > 0 ? queuedCount : undefined },
    { to: '/proof', icon: Wrench, label: t('nav.proof') },
    { to: '/demo', icon: SlidersHorizontal, label: t('nav.demo') },
    { to: '/privacy', icon: ShieldCheck, label: t('nav.privacy') },
    { to: '/about', icon: Info, label: t('nav.about') },
  ]

  return (
    <>
      <div className="hero-banner">
        <div>
          <p className="hero-greeting">
            {profileName ? `${t('dashboard.welcomeBack')}, ${profileName}` : t('dashboard.welcomeBack')}
          </p>
          <div className="hero-date">{heroDate}</div>
        </div>
        {waveHeight != null && (
          <div className="hero-weather-pill">
            <Waves size={18} aria-hidden="true" />
            <span>{waveHeight}m {t('dashboard.waves')}{seaTemp != null ? ` · ${seaTemp}°C` : ''}</span>
          </div>
        )}
      </div>

      <div className="stats-row">
        <div className="stat-chip">
          <Fish className="stat-chip-icon" size={20} aria-hidden="true" />
          <div className="stat-chip-label">{t('dashboard.todayCatches')}</div>
          <div className="stat-chip-value">{Math.round(todayAnimated)}</div>
        </div>
        <div className="stat-chip">
          <CloudOff className="stat-chip-icon" size={20} aria-hidden="true" />
          <div className="stat-chip-label">{t('dashboard.queued')}</div>
          <div className="stat-chip-value">{Math.round(queuedAnimated)}</div>
        </div>
        <div className="stat-chip">
          <Thermometer className="stat-chip-icon" size={20} aria-hidden="true" />
          <div className="stat-chip-label">{t('marine.sst')}</div>
          <div className="stat-chip-value">{seaTemp == null ? '--' : `${seaTempAnimated.toFixed(1)}°C`}</div>
        </div>
        <div className="stat-chip">
          <Calendar className="stat-chip-icon" size={20} aria-hidden="true" />
          <div className="stat-chip-label">{t('dashboard.lastTrip')}</div>
          <div className="stat-chip-value">{lastTripDate ? formatNiceDate(lastTripDate) : '--'}</div>
        </div>
      </div>

      <div className="bento-grid">
        <Link to="/catch" className="bento-card bento-feature">
          <Camera className="bento-icon" size={32} aria-hidden="true" />
          <div className="bento-title">{t('nav.catch')}</div>
          <div className="bento-sub">{t('dashboard.recordCatchFlow')}</div>
        </Link>

        <Link to="/marine" className="bento-card">
          <Waves className="bento-icon" size={28} aria-hidden="true" />
          <div className="bento-title">{t('nav.marine')}</div>
          {waveHeight != null && <div className="bento-value">{waveHeight} m</div>}
          <div className="bento-sub">{t('dashboard.checkBeforeHeadingOut')}</div>
        </Link>

        <Link to="/history" className="bento-card">
          <BookOpen className="bento-icon" size={28} aria-hidden="true" />
          <div className="bento-title">{t('nav.history')}</div>
          <div className="bento-sub">
            {catches.length === 0 ? t('dashboard.noCatchesYet') : `${distinctSpecies} ${t('dashboard.speciesLogged')}`}
          </div>
          {catches.length > 0 && (
            <div className="bento-avatars">
              {catches.slice(0, 2).map((c, i) => (
                <Avatar key={String(c.id)} label={speciesLabel(String(c.species_id))} index={i} />
              ))}
            </div>
          )}
        </Link>

        <Link to="/declaration" className="bento-card">
          <Anchor className="bento-icon" size={28} aria-hidden="true" />
          <div className="bento-title">{t('nav.declaration')}</div>
          <div className="bento-sub">{t('dashboard.declarationPrompt')}</div>
        </Link>
      </div>

      <div className="more-tools-row">
        {toolButtons.map((btn) => (
          <Link key={btn.to} to={btn.to} className="tool-btn" aria-label={btn.label}>
            <btn.icon size={20} aria-hidden="true" />
            <span>{btn.label}</span>
            {btn.badge != null && <span className="tool-btn-badge">{btn.badge}</span>}
          </Link>
        ))}
      </div>

      <div className="card">
        {/* h2, not h3: the shell wordmark is this page's h1, so a section
            heading at h3 skipped a level (h1 -> h3). The empty-state title
            below is h3 because it sits INSIDE this section. */}
        <div className="recent-activity-header">
          <h2>{t('dashboard.recentActivity')}</h2>
          {catches.length > 0 && <Link to="/history">{t('dashboard.viewAll')}</Link>}
        </div>

        {catches.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon-wrap">
              <div className="empty-state-arc" aria-hidden="true" />
              <Fish size={64} strokeWidth={1.5} aria-hidden="true" />
            </div>
            <h3>{t('dashboard.readyWhenYouAre')}</h3>
            <p className="bento-sub">{t('dashboard.emptyStateBody')}</p>
            <Link to="/catch" className="primary">{t('dashboard.recordFirstCatch')}</Link>
          </div>
        ) : (
          recentThree.map((c, i) => (
            <div className="recent-activity-row" key={String(c.id)}>
              <Avatar label={speciesLabel(String(c.species_id))} index={i} size="lg" />
              <div className="recent-activity-info">
                <div className="recent-activity-species">{speciesLabel(String(c.species_id))}</div>
                <div className="recent-activity-time">{formatRelativeActivity(c.created_at as string, t)}</div>
              </div>
            </div>
          ))
        )}
      </div>

      <p className="banner info">{t('limitation.permanent')}</p>

      {/* Nemo. Fixed to the viewport corner, so it sits outside the bento grid
          rather than at the end of it. `autoOpen` is honoured only here: Home is
          where a fisher lands, so it is the one place a greeting is not an
          interruption of a task already in progress. */}
      <AssistantBot autoOpen />
    </>
  )
}
