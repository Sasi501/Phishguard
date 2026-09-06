import './ErrorBanner.css'

interface ErrorBannerProps {
  message: string
  onDismiss: () => void
}

export default function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
  return (
    <div role="alert" className="error-banner">
      <p className="error-banner__message">{message}</p>
      <button
        className="error-banner__dismiss"
        onClick={onDismiss}
        aria-label="Dismiss error"
        type="button"
      >
        ×
      </button>
    </div>
  )
}
