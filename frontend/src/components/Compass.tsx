type Props = {
  waveDeg: number | null
  swellDeg: number | null
  waveLabel: string
  swellLabel: string
}

export default function Compass({ waveDeg, swellDeg, waveLabel, swellLabel }: Props) {
  const needle = (deg: number, color: string, key: string) => {
    const rad = ((deg - 90) * Math.PI) / 180
    const x2 = 50 + 34 * Math.cos(rad)
    const y2 = 50 + 34 * Math.sin(rad)
    return (
      <line key={key} x1="50" y1="50" x2={x2} y2={y2}
        stroke={color} strokeWidth="3" strokeLinecap="round" />
    )
  }

  return (
    <div className="compass">
      <svg viewBox="0 0 100 100" role="img" aria-label={`${waveLabel} ${waveDeg ?? '—'}°, ${swellLabel} ${swellDeg ?? '—'}°`}>
        <circle cx="50" cy="50" r="46" fill="none" stroke="var(--border-subtle)" strokeWidth="2" />
        <circle cx="50" cy="50" r="3" fill="var(--text-secondary)" />
        <text x="50" y="12" textAnchor="middle" className="compass-label">N</text>
        <text x="91" y="54" textAnchor="middle" className="compass-label">E</text>
        <text x="50" y="96" textAnchor="middle" className="compass-label">S</text>
        <text x="9" y="54" textAnchor="middle" className="compass-label">W</text>
        {typeof waveDeg === 'number' && needle(waveDeg, 'var(--accent-teal)', 'wave')}
        {typeof swellDeg === 'number' && needle(swellDeg, 'var(--primary-coral)', 'swell')}
      </svg>
      <div className="compass-legend">
        <span><i style={{ background: 'var(--accent-teal)' }} />{waveLabel}{typeof waveDeg === 'number' ? ` ${waveDeg}°` : ''}</span>
        <span><i style={{ background: 'var(--primary-coral)' }} />{swellLabel}{typeof swellDeg === 'number' ? ` ${swellDeg}°` : ''}</span>
      </div>
    </div>
  )
}
