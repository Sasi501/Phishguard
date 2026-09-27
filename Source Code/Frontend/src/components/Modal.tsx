import './Modal.css'

import { useEffect, useRef } from 'react'

interface ModalProps {
  title?: string
  message: string
  onConfirm: () => void
  onCancel: () => void
  confirmLabel?: string
  cancelLabel?: string
}

export default function Modal({ title, message, onConfirm, onCancel, confirmLabel = 'Confirm', cancelLabel = 'Cancel' }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null
    const dialog = dialogRef.current
    const focusable = dialog?.querySelectorAll<HTMLElement>('button:not([disabled])') ?? []
    focusable[0]?.focus()

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onCancel()
        return
      }
      if (event.key !== 'Tab' || focusable.length === 0) return

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      previousFocus?.focus()
    }
  }, [onCancel])

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label={title ? undefined : 'Confirmation'}>
      <div className="modal-card" ref={dialogRef} aria-labelledby={title ? 'modal-title' : undefined} aria-describedby="modal-description">
        {title && <h3 id="modal-title" className="modal-title">{title}</h3>}
        <div id="modal-description" className="modal-body">{message}</div>
        <div className="modal-actions">
          <button type="button" className="modal-btn modal-btn--cancel" onClick={onCancel}>{cancelLabel}</button>
          <button type="button" className="modal-btn modal-btn--confirm" onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  )
}
