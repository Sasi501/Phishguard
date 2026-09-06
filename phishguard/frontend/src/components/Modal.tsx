import React from 'react'
import './Modal.css'

interface ModalProps {
  title?: string
  message: string
  onConfirm: () => void
  onCancel: () => void
  confirmLabel?: string
  cancelLabel?: string
}

export default function Modal({ title, message, onConfirm, onCancel, confirmLabel = 'Confirm', cancelLabel = 'Cancel' }: ModalProps) {
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-card">
        {title && <h3 className="modal-title">{title}</h3>}
        <div className="modal-body">{message}</div>
        <div className="modal-actions">
          <button className="modal-btn modal-btn--cancel" onClick={onCancel}>{cancelLabel}</button>
          <button className="modal-btn modal-btn--confirm" onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  )
}
