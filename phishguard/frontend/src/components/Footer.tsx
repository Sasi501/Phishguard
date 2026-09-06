import React from 'react';
import './Footer.css';

const Footer: React.FC = () => {
  return (
    <footer className="footer glass-card">
      <div className="footer-content">
        <div className="footer-column">
          <h3 className="footer-brand">PhishGuard</h3>
          <p className="footer-tagline">Advanced AI-powered phishing detection and threat intelligence.</p>
        </div>
        
        <div className="footer-column">
          <h4 className="footer-heading">Quick Links</h4>
          <ul className="footer-links">
            <li><a href="#" className="footer-link">GitHub</a></li>
            <li><a href="#" className="footer-link">Documentation</a></li>
            <li><a href="#" className="footer-link">API Reference</a></li>
          </ul>
        </div>
        
        <div className="footer-column">
          <h4 className="footer-heading">Tech Stack</h4>
          <ul className="footer-links">
            <li><span className="footer-text">React & TypeScript</span></li>
            <li><span className="footer-text">FastAPI Python</span></li>
            <li><span className="footer-text">CatBoost Model</span></li>
            <li><span className="footer-text">ONNX Runtime</span></li>
          </ul>
        </div>
      </div>
      
      <div className="footer-bottom">
        <div className="footer-copyright">
          &copy; 2026 PhishGuard &mdash; Built with AI
        </div>
        <div className="footer-version">
          v1.0.0
        </div>
      </div>
    </footer>
  );
};

export default Footer;
