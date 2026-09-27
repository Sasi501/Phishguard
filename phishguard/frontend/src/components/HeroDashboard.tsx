import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import './HeroDashboard.css'

interface HeroDashboardProps {
  onStartScan: () => void
}

function useCountUp(end: number, duration: number = 1000) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let startTime: number | null = null;
    const startValue = count;
    const endValue = end;

    if (startValue === endValue) return;

    const step = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      const easeOutQuart = 1 - Math.pow(1 - progress, 4);
      
      setCount(Math.floor(startValue + (endValue - startValue) * easeOutQuart));

      if (progress < 1) {
        window.requestAnimationFrame(step);
      } else {
        setCount(endValue);
      }
    };

    window.requestAnimationFrame(step);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [end, duration]);

  return count;
}

const ShieldIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
  </svg>
)

const ScanIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <path d="M12 2v10l5 5" />
    <circle cx="12" cy="12" r="2" />
  </svg>
)

const CpuIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="4" y="4" width="16" height="16" rx="2" ry="2"/>
    <rect x="9" y="9" width="6" height="6"/>
    <line x1="9" y1="1" x2="9" y2="4"/>
    <line x1="15" y1="1" x2="15" y2="4"/>
    <line x1="9" y1="20" x2="9" y2="23"/>
    <line x1="15" y1="20" x2="15" y2="23"/>
    <line x1="20" y1="9" x2="23" y2="9"/>
    <line x1="20" y1="14" x2="23" y2="14"/>
    <line x1="1" y1="9" x2="4" y2="9"/>
    <line x1="1" y1="14" x2="4" y2="14"/>
  </svg>
)

export default function HeroDashboard({ onStartScan }: HeroDashboardProps) {
  const { t } = useTranslation()
  const [threatsBlocked, setThreatsBlocked] = useState<number | null>(null)
  const [totalScans, setTotalScans] = useState<number | null>(null)
  const [activeEngines, setActiveEngines] = useState<number | null>(null)
  const [statsAvailable, setStatsAvailable] = useState(false)

  const animatedThreats = useCountUp(threatsBlocked ?? 0)
  const animatedScans = useCountUp(totalScans ?? 0)
  const animatedEngines = useCountUp(activeEngines ?? 0)

  // Fetch real stats from the backend
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('/api/stats/')
        if (!response.ok) throw new Error(`Stats request failed: ${response.status}`)
        const data: unknown = await response.json()
        if (!data || typeof data !== 'object') throw new Error('Stats response is invalid')

        const stats = data as Record<string, unknown>
        const total = stats.total_scans
        const threats = stats.threats_blocked
        const engines = stats.active_engines
        setTotalScans(typeof total === 'number' && Number.isFinite(total) ? total : null)
        setThreatsBlocked(typeof threats === 'number' && Number.isFinite(threats) ? threats : null)
        setActiveEngines(typeof engines === 'number' && Number.isFinite(engines) ? engines : null)
        setStatsAvailable(true)
      } catch {
        setTotalScans(null)
        setThreatsBlocked(null)
        setActiveEngines(null)
        setStatsAvailable(false)
      }
    }

    void fetchStats()
    const interval = setInterval(() => void fetchStats(), 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <section className="hero-dashboard">
      <div className="hero-dashboard__hex-grid" aria-hidden="true" />
      <div className="hero-dashboard__glow" aria-hidden="true" />
      
      <div className="hero-dashboard__content">
        <h1 className="hero-dashboard__title">
          {t('hero.title')}
        </h1>
        <p className="hero-dashboard__subtitle">
          {t('hero.subtitle')}
        </p>

        <div className="hero-dashboard__stats">
          <div className="hero-stat glass-card card-1">
            <div className="hero-stat__icon text-neon-crimson"><ShieldIcon /></div>
            <span className="hero-stat__value text-neon-crimson">{statsAvailable && threatsBlocked !== null ? animatedThreats.toLocaleString() : 'Unavailable'}</span>
            <span className="hero-stat__label">{t('hero.threats_blocked')}</span>
          </div>
          <div className="hero-stat glass-card card-2">
            <div className="hero-stat__icon text-neon-cyan"><ScanIcon /></div>
            <span className="hero-stat__value text-neon-cyan">{statsAvailable && totalScans !== null ? animatedScans.toLocaleString() : 'Unavailable'}</span>
            <span className="hero-stat__label">{t('hero.total_scans')}</span>
          </div>
          <div className="hero-stat glass-card card-3">
            <div className="hero-stat__icon text-neon-green"><CpuIcon /></div>
            <span className="hero-stat__value text-neon-green">{statsAvailable && activeEngines !== null ? animatedEngines : 'Unavailable'}</span>
            <span className="hero-stat__label">{t('hero.active_engines')}</span>
          </div>
        </div>

        <div className="hero-dashboard__cta-wrapper">
          <div className="hero-dashboard__cta-ring" aria-hidden="true" />
          <button 
            className="hero-dashboard__cta" 
            onClick={onStartScan}
          >
            {t('hero.start_scan')}
          </button>
        </div>
      </div>
    </section>
  )
}
