import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import './SettingsPanel.css'

interface SettingsPanelProps {
  onClose: () => void
}

export default function SettingsPanel({ onClose }: SettingsPanelProps) {
  const { t, i18n } = useTranslation()
  const [reducedMotion, setReducedMotion] = useState(
    localStorage.getItem('reducedMotion') === 'true'
  )

  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    i18n.changeLanguage(e.target.value)
    localStorage.setItem('language', e.target.value)
  }

  const handleMotionToggle = () => {
    const newMotion = !reducedMotion
    setReducedMotion(newMotion)
    if (newMotion) {
      document.documentElement.classList.add('reduced-motion')
    } else {
      document.documentElement.classList.remove('reduced-motion')
    }
    localStorage.setItem('reducedMotion', String(newMotion))
  }

  useEffect(() => {
    const savedLang = localStorage.getItem('language')
    if (savedLang && savedLang !== i18n.language) {
      void i18n.changeLanguage(savedLang)
    }
    document.documentElement.classList.toggle('reduced-motion', reducedMotion)
  }, [i18n, reducedMotion])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <aside className="settings-panel glass-card" aria-labelledby="settings-panel-title">
      <div className="settings-panel__header">
        <h2 id="settings-panel-title">{t('settings.title')}</h2>
        <button className="settings-panel__close" onClick={onClose} aria-label={t('settings.close')}>✕</button>
      </div>

      <div className="settings-panel__content">
        <div className="settings-panel__group">
          <label htmlFor="settings-language">{t('settings.language')}</label>
          <select id="settings-language" value={i18n.language} onChange={handleLanguageChange} className="settings-panel__select">
            <option value="en">English</option>
            <option value="hi">हिंदी (Hindi)</option>
            <option value="ta">தமிழ் (Tamil)</option>
            <option value="fr">Français (French)</option>
          </select>
        </div>

        <div className="settings-panel__group">
          <span className="settings-panel__group-label">{t('settings.animations')}</span>
          <label className="settings-panel__checkbox-label">
            <input 
              type="checkbox" 
              checked={reducedMotion} 
              onChange={handleMotionToggle}
            />
            {t('settings.reduced_motion')}
          </label>
        </div>
      </div>
    </aside>
  )
}
