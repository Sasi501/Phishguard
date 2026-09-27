import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import './NavigationBar.css'

type Props = {
  viewMode: 'basic' | 'advanced'
  onViewModeChange: (mode: 'basic' | 'advanced') => void
  onToggleRegistry?: () => void
  onToggleHITL?: () => void
  onToggleSettings?: () => void
  onToggleEvaluation?: () => void
  onToggleAnalytics?: () => void
  isRegistryOpen?: boolean
  isHITLOpen?: boolean
  isEvaluationOpen?: boolean
  isAnalyticsOpen?: boolean
}

export default function NavigationBar({
  viewMode,
  onViewModeChange,
  onToggleRegistry,
  onToggleHITL,
  onToggleSettings,
  onToggleEvaluation,
  onToggleAnalytics,
  isRegistryOpen,
  isHITLOpen,
  isEvaluationOpen,
  isAnalyticsOpen,
}: Props) {
  const { t } = useTranslation()
  const [coreOnline, setCoreOnline] = useState<boolean | null>(null)

  useEffect(() => {
    let cancelled = false

    const checkHealth = async () => {
      try {
        const response = await fetch('/api/health/')
        if (!response.ok) throw new Error(`Health request failed: ${response.status}`)
        const health: { status?: string } = await response.json()
        if (!cancelled) {
          setCoreOnline(health.status?.toLowerCase() === 'ok' || health.status?.toLowerCase() === 'healthy')
        }
      } catch {
        if (!cancelled) setCoreOnline(false)
      }
    }

    void checkHealth()
    const interval = window.setInterval(() => void checkHealth(), 30000)
    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [])

  return (
    <nav role="navigation" aria-label="Main navigation" className="nav-bar">
      <div className="nav-bar__logo-container">
        <svg className="nav-bar__logo-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        </svg>
        <span className="nav-bar__logo">PHISHGUARD</span>
      </div>
      <div className="nav-bar__mode-switch" role="group" aria-label="View Mode">
        <button
          type="button"
          className={`nav-bar__mode-btn ${viewMode === 'basic' ? 'nav-bar__mode-btn--active' : ''}`}
          onClick={() => onViewModeChange('basic')}
          aria-pressed={viewMode === 'basic'}
        >
          <span className="nav-bar__mode-icon">⚡</span>
          Basic View
        </button>
        <button
          type="button"
          className={`nav-bar__mode-btn ${viewMode === 'advanced' ? 'nav-bar__mode-btn--active' : ''}`}
          onClick={() => onViewModeChange('advanced')}
          aria-pressed={viewMode === 'advanced'}
        >
          <span className="nav-bar__mode-icon">🔬</span>
          Advanced Analysis
        </button>
      </div>

      <div className="nav-bar__actions">
        {viewMode === 'advanced' && (
          <>
            <button
              className={`nav-bar__button ${isAnalyticsOpen ? 'nav-bar__button--active' : ''}`}
              onClick={onToggleAnalytics}
              aria-label="Toggle scan analytics"
            >
              <span className="nav-bar__btn-text">Analytics</span>
            </button>
            <button
              className={`nav-bar__button ${isEvaluationOpen ? 'nav-bar__button--active' : ''}`}
              onClick={onToggleEvaluation}
              aria-label="Toggle model evaluation center"
            >
              <span className="nav-bar__btn-text">Evaluation</span>
            </button>
            <button
              className={`nav-bar__button ${isRegistryOpen ? 'nav-bar__button--active' : ''}`}
              onClick={onToggleRegistry}
              aria-label="Toggle registry"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-bar__btn-icon">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
              </svg>
              <span className="nav-bar__btn-text">{t('nav.registry')}</span>
            </button>
            <button
              className={`nav-bar__button ${isHITLOpen ? 'nav-bar__button--active' : ''}`}
              onClick={onToggleHITL}
              aria-label="Toggle HITL panel"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-bar__btn-icon">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
              </svg>
              <span className="nav-bar__btn-text">{t('nav.hitl')}</span>
            </button>
          </>
        )}
        <button 
          className="nav-bar__button nav-bar__button--settings" 
          onClick={onToggleSettings} 
          aria-label={t('nav.settings')}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-bar__btn-icon nav-bar__btn-icon--settings">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
        </button>
      </div>
      <div className="nav-bar__status">
        <span className={`nav-bar__status-dot nav-bar__status-dot--${coreOnline === null ? 'checking' : coreOnline ? 'online' : 'unavailable'}`} aria-hidden="true" />
        <span className="nav-bar__status-text" role="status">
          {t(coreOnline === null ? 'nav.core_checking' : coreOnline ? 'nav.core_online' : 'nav.core_unavailable')}
        </span>
      </div>
    </nav>
  )
}
