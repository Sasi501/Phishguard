import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { AnalyzeRequest } from '../types/api'
import { SIZES } from '../theme'
import './ScannerPanel.css'

interface ScannerPanelProps {
  loading: boolean
  onSubmit: (req: AnalyzeRequest) => void
}

const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp']

export default function ScannerPanel({ loading, onSubmit }: ScannerPanelProps) {
  const { t } = useTranslation()
  const [url, setUrl] = useState('')
  const [text, setText] = useState('')
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [urlError, setUrlError] = useState('')
  const [imageError, setImageError] = useState('')
  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null
    if (!file) {
      setImageFile(null)
      setImageError('')
      return
    }
    if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
      setImageFile(null)
      setImageError('Only image files (JPEG, PNG, GIF, WebP, BMP) are accepted.')
      return
    }
    if (file.size > SIZES.imageSizeLimit) {
      setImageFile(null)
      setImageError('File size must not exceed 10 MB.')
      return
    }
    setImageFile(file)
    setImageError('')
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setUrlError('')

    if (!url.trim()) {
      setUrlError('Target URL is required.')
      return
    }
    if (!/^https?:\/\//i.test(url.trim())) {
      setUrlError('Enter a valid URL including http:// or https://')
      return
    }

    onSubmit({ url: url.trim(), text: text.trim() || undefined, image: imageFile ?? undefined })
  }

  return (
    <section className="scanner-panel glass-card" aria-label="URL scanner">
      {loading && (
        <>
          <div className="scanner-panel__scan-line" aria-hidden="true" />
          <div className="scanner-panel__loading-status" aria-live="polite" aria-atomic="true">
            <div className="scanner-panel__spinner" aria-hidden="true" />
            <span>Analyzing multi-modal signals...</span>
          </div>
        </>
      )}

      <form onSubmit={handleSubmit} noValidate className="scanner-panel__form">
        <div className="scanner-panel__field">
          <label htmlFor="scanner-url" className="scanner-panel__label">
            {t('scanner.target_url')}
          </label>
          <input
            id="scanner-url"
            type="url"
            className={`scanner-panel__input${urlError ? ' scanner-panel__input--error' : ''}`}
            placeholder={t('scanner.target_url_placeholder')}
            value={url}
            onChange={e => { setUrl(e.target.value); if (urlError) setUrlError('') }}
            disabled={loading}
            autoComplete="off"
            aria-describedby={urlError ? 'scanner-url-error' : undefined}
          />
          {urlError && (
            <span id="scanner-url-error" className="scanner-panel__field-error" role="alert">
              {urlError}
            </span>
          )}
        </div>

        <div className="scanner-panel__advanced-toggle">
          <button
            type="button"
            className="scanner-panel__toggle-btn"
            aria-expanded={showAdvanced}
            aria-controls="advanced-options-panel"
            onClick={() => setShowAdvanced(v => !v)}
            disabled={loading}
          >
            <span aria-hidden="true">{showAdvanced ? '▲' : '▼'}</span>
            {t('scanner.advanced_options')}
          </button>
        </div>

        <div
          id="advanced-options-panel"
          className="scanner-panel__advanced-content"
          hidden={!showAdvanced}
        >
          <div className="scanner-panel__field">
            <label htmlFor="scanner-text" className="scanner-panel__label">
              {t('scanner.page_text')}
            </label>
            <textarea
              id="scanner-text"
              className="scanner-panel__textarea"
              placeholder="Paste page text…"
              value={text}
              onChange={e => setText(e.target.value)}
              disabled={loading}
              rows={4}
            />
          </div>

          <div className="scanner-panel__field">
            <label htmlFor="scanner-image" className="scanner-panel__label">
              {t('scanner.screenshot')}
            </label>
            <input
              id="scanner-image"
              type="file"
              className="scanner-panel__file-input"
              accept="image/jpeg,image/png,image/gif,image/webp,image/bmp"
              onChange={handleImageChange}
              disabled={loading}
              aria-describedby={imageError ? 'scanner-image-error' : undefined}
            />
            {imageError && (
              <span id="scanner-image-error" className="scanner-panel__field-error" role="alert">
                {imageError}
              </span>
            )}
          </div>
        </div>

        <button
          type="submit"
          className="scanner-panel__submit"
          disabled={loading}
          aria-busy={loading}
        >
          {loading ? t('scanner.scanning') : t('scanner.scan_target')}
        </button>
      </form>
    </section>
  )
}
