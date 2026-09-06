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

  // Effect to set initial language from local storage if available
  useEffect(() => {
    const savedLang = localStorage.getItem('language')
    if (savedLang && savedLang !== i18n.language) {
      i18n.changeLanguage(savedLang)
    }
  }, [i18n])

  return (
    <div className="settings-panel glass-card">
      <div className="settings-panel__header">
        <h2>{t('settings.title')}</h2>
        <button className="settings-panel__close" onClick={onClose} aria-label={t('settings.close')}>✕</button>
      </div>

      <div className="settings-panel__content">
        <div className="settings-panel__group">
          <label>{t('settings.language')}</label>
          <select value={i18n.language} onChange={handleLanguageChange} className="settings-panel__select">
            <option value="en">English</option>
            <option value="hi">हिंदी (Hindi)</option>
            <option value="ta">தமிழ் (Tamil)</option>
            <option value="fr">Français (French)</option>
          </select>
        </div>

        <div className="settings-panel__group">
          <label>{t('settings.animations')}</label>
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
    </div>
  )
}
