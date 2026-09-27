import React from 'react';
import './ComingSoonModal.css';

interface ComingSoonModalProps {
  title: string;
  description: string;
  category: 'docs' | 'api' | 'general';
  onClose: () => void;
}

const ComingSoonModal: React.FC<ComingSoonModalProps> = ({
  title,
  description,
  category,
  onClose,
}) => {
  return (
    <div className="cs-backdrop" onClick={onClose}>
      <div className="cs-modal glass-card" onClick={(e) => e.stopPropagation()}>
        <div className="cs-glow"></div>
        
        <button className="cs-close-btn" onClick={onClose} aria-label="Close modal">
          ✕
        </button>

        <div className="cs-icon-wrapper">
          <svg className="cs-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            {category === 'api' ? (
              <>
                <polyline points="16 18 22 12 16 6" />
                <polyline points="8 6 2 12 8 18" />
              </>
            ) : (
              <>
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
              </>
            )}
          </svg>
        </div>

        <div className="cs-status-tag">
          <span className="cs-pulse-dot"></span>
          Under Development
        </div>

        <h3 className="cs-title">{title}</h3>
        <p className="cs-description">{description}</p>

        <div className="cs-roadmap">
          <h4>Expected Features in Release v2.1:</h4>
          <ul>
            {category === 'api' ? (
              <>
                <li>Interactive OpenAPI 3.0 & Swagger UI schemas</li>
                <li>Real-time WebSocket threat stream endpoints</li>
                <li>Rate-limited REST scan API with Bearer token authentication</li>
              </>
            ) : (
              <>
                <li>Full architecture breakdown & AI model explainability guides</li>
                <li>Chrome Extension deployment and sideloading documentation</li>
                <li>HITL (Human-in-the-Loop) verification system handbook</li>
              </>
            )}
          </ul>
        </div>

        <div className="cs-actions">
          {category === 'api' && (
            <a
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="cs-btn-secondary"
            >
              Open Local Swagger Docs ↗
            </a>
          )}
          <a
            href="https://github.com/Sasi501/Phishguard"
            target="_blank"
            rel="noopener noreferrer"
            className="cs-btn-primary"
          >
            Visit GitHub Repository ↗
          </a>
        </div>
      </div>
    </div>
  );
};

export default ComingSoonModal;
