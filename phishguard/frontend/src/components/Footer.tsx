import React, { useState } from 'react';
import './Footer.css';
import ComingSoonModal from './ComingSoonModal';

const Footer: React.FC = () => {
  const [modalConfig, setModalConfig] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    category: 'docs' | 'api' | 'general';
  }>({
    isOpen: false,
    title: '',
    description: '',
    category: 'general',
  });

  const openModal = (
    title: string,
    description: string,
    category: 'docs' | 'api' | 'general'
  ) => {
    setModalConfig({
      isOpen: true,
      title,
      description,
      category,
    });
  };

  const closeModal = () => {
    setModalConfig((prev) => ({ ...prev, isOpen: false }));
  };

  return (
    <>
      <footer className="footer glass-card">
        <div className="footer-content">
          <div className="footer-column footer-brand-column">
            <h3 className="footer-brand">PhishGuard</h3>
            <p className="footer-tagline">
              Next-generation AI ensemble cybersecurity system for real-time phishing detection,
              explainability, and automated browser protection.
            </p>
            <div className="footer-social-links">
              <a
                href="https://github.com/Sasi501/Phishguard"
                target="_blank"
                rel="noopener noreferrer"
                className="footer-social-btn"
                title="View on GitHub"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
                </svg>
                <span>GitHub Repository</span>
              </a>
            </div>
          </div>

          <div className="footer-column">
            <h4 className="footer-heading">Quick Links</h4>
            <ul className="footer-links">
              <li>
                <a
                  href="https://github.com/Sasi501/Phishguard"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="footer-link"
                >
                  GitHub ↗
                </a>
              </li>
              <li>
                <button
                  type="button"
                  onClick={() =>
                    openModal(
                      'Documentation Portal',
                      'Comprehensive developer docs, system architecture diagrams, model explainability guides, and side-loading setup instructions are currently in production.',
                      'docs'
                    )
                  }
                  className="footer-link-btn"
                >
                  Documentation <span className="footer-badge-soon">Soon</span>
                </button>
              </li>
              <li>
                <button
                  type="button"
                  onClick={() =>
                    openModal(
                      'API Reference',
                      'The PhishGuard API exposes fast endpoints for URL scanning, ensemble fusion inference, and explainability telemetry.',
                      'api'
                    )
                  }
                  className="footer-link-btn"
                >
                  API Reference <span className="footer-badge-soon">Soon</span>
                </button>
              </li>
            </ul>
          </div>

          <div className="footer-column">
            <h4 className="footer-heading">Tech Stack</h4>
            <ul className="footer-links">
              <li>
                <a
                  href="https://react.dev/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="footer-link tech-link"
                >
                  React & TypeScript ↗
                </a>
              </li>
              <li>
                <a
                  href="https://fastapi.tiangolo.com/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="footer-link tech-link"
                >
                  FastAPI Python ↗
                </a>
              </li>
              <li>
                <a
                  href="https://catboost.ai/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="footer-link tech-link"
                >
                  CatBoost ML ↗
                </a>
              </li>
              <li>
                <a
                  href="https://onnxruntime.ai/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="footer-link tech-link"
                >
                  ONNX Runtime ↗
                </a>
              </li>
              <li>
                <a
                  href="https://ai.google.dev/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="footer-link tech-link"
                >
                  Google Gemini AI ↗
                </a>
              </li>
              <li>
                <a
                  href="https://www.mongodb.com/atlas"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="footer-link tech-link"
                >
                  MongoDB Atlas ↗
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="footer-bottom">
          <div className="footer-copyright">
            &copy; 2026 <a href="https://github.com/Sasi501/Phishguard" target="_blank" rel="noopener noreferrer" className="footer-bottom-link">PhishGuard</a> &mdash; Advanced AI Cybersecurity Ensemble
          </div>
          <div className="footer-version">
            v2.0.0 Enterprise
          </div>
        </div>
      </footer>

      {modalConfig.isOpen && (
        <ComingSoonModal
          title={modalConfig.title}
          description={modalConfig.description}
          category={modalConfig.category}
          onClose={closeModal}
        />
      )}
    </>
  );
};

export default Footer;
