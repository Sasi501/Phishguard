import './RoadmapPanel.css'

export default function RoadmapPanel() {
  return (
    <aside className="roadmap-panel" aria-label="Project roadmap">
      <h2>Future Roadmap (Highlights)</h2>
      <ol>
        <li>
          <strong>Advanced Phishing Detection</strong>
          <ul>
            <li>Redirect chain unwrapper, shortener expansion, QR/quishing detection</li>
            <li>Homograph/IDN detection, DNS & certificate intelligence</li>
          </ul>
        </li>
        <li>
          <strong>Multi-Modal Intelligence 2.0</strong>
          <ul>
            <li>Fuse URL, email text, HTML/DOM, screenshot, DNS/WHOIS, and TI signals</li>
          </ul>
        </li>
        <li>
          <strong>Adaptive AI</strong>
          <ul>
            <li>Drift detection, continuous evaluation, retraining, user feedback loop</li>
          </ul>
        </li>
        <li>
          <strong>AI Security Agent</strong>
          <ul>
            <li>Autonomous investigation: collect signals, explain decisions, decide allow/warn/block</li>
          </ul>
        </li>
        <li>
          <strong>Privacy-Preserving Detection</strong>
          <ul>
            <li>On-device inference, differential privacy, telemetry controls</li>
          </ul>
        </li>
        <li>
          <strong>Multilingual Detection</strong>
          <ul>
            <li>Support regional languages (Hindi, Tamil, Malayalam, Telugu, Kannada, Bengali, Arabic)</li>
          </ul>
        </li>
        <li>
          <strong>Cross-Platform Protection</strong>
          <ul>
            <li>Support browsers, email clients, mobile, enterprise gateways, SOC integrations</li>
          </ul>
        </li>
        <li>
          <strong>Beyond Phishing</strong>
          <ul>
            <li>Modules: communication safety, web safety, content safety, identity protection</li>
          </ul>
        </li>
        <li>
          <strong>Threat Intelligence & Global Learning</strong>
          <ul>
            <li>Integrate PhishTank, OpenPhish, VirusTotal, AbuseIPDB, CT logs</li>
          </ul>
        </li>
        <li>
          <strong>Adversarial AI Protection</strong>
          <ul>
            <li>Adversarial training, robustness testing, model disagreement detection</li>
          </ul>
        </li>
      </ol>
    </aside>
  )
}
