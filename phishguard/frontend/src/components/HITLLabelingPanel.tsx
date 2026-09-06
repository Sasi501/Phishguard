import React, { useState, useEffect, useCallback } from 'react';
import './HITLLabelingPanel.css';

interface PendingItem {
  id: number;
  url: string;
  user_label: string;
  status: string;
  created_at: number;
}

interface AuditLog {
  id: number;
  url: string;
  action: string;
  reviewer: string;
  timestamp: number;
}

export default function HITLLabelingPanel() {
  const [pendingList, setPendingList] = useState<PendingItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [adminKey, setAdminKey] = useState<string>('');
  const [manualUrl, setManualUrl] = useState<string>('');
  const [manualLabel, setManualLabel] = useState<string>('phishing');
  const [status, setStatus] = useState<string | null>(null);
  const [isAuthorized, setIsAuthorized] = useState<boolean>(false);

  const fetchReviews = useCallback(async () => {
    if (!adminKey) {
      setPendingList([]);
      setAuditLogs([]);
      setIsAuthorized(false);
      return;
    }
    
    setStatus('Loading pending reviews...');
    try {
      const headers: Record<string, string> = { 'X-ADMIN-KEY': adminKey };
      const [pendingRes, auditRes] = await Promise.all([
        fetch('/api/hitl/pending/', { headers }),
        fetch('/api/hitl/audit-logs/', { headers })
      ]);

      if (!pendingRes.ok || !auditRes.ok) {
        setPendingList([]);
        setAuditLogs([]);
        setIsAuthorized(false);
        setStatus('Unauthorized or invalid Admin Key.');
        return;
      }

      const pendingData = await pendingRes.json();
      const auditData = await auditRes.json();
      
      setPendingList(pendingData);
      setAuditLogs(auditData.reverse()); // Show newest first
      setIsAuthorized(true);
      setStatus(null);
    } catch (e) {
      setPendingList([]);
      setAuditLogs([]);
      setIsAuthorized(false);
      setStatus('Failed to query HITL endpoints.');
    }
  }, [adminKey]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (adminKey) {
        fetchReviews();
      }
    }, 500); // Debounce key typing
    return () => clearTimeout(timer);
  }, [adminKey, fetchReviews]);

  const handleResolve = async (url: string, finalLabel: string) => {
    setStatus(`Resolving URL as ${finalLabel}...`);
    try {
      const form = new FormData();
      form.append('url', url);
      form.append('final_label', finalLabel);
      form.append('reviewer', 'admin');

      const response = await fetch('/api/hitl/resolve/', {
        method: 'POST',
        headers: { 'X-ADMIN-KEY': adminKey },
        body: form
      });

      if (!response.ok) {
        const err = await response.json();
        setStatus(`Error resolving URL: ${err.detail || response.statusText}`);
        return;
      }

      setStatus(`Successfully resolved URL as ${finalLabel}.`);
      fetchReviews(); // Refresh lists
    } catch (e) {
      setStatus('Network error resolving URL.');
    }
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualUrl) return;
    setStatus('Submitting URL to review queue...');
    try {
      const form = new FormData();
      form.append('url', manualUrl);
      form.append('user_label', manualLabel);

      const response = await fetch('/api/hitl/submit/', {
        method: 'POST',
        body: form
      });

      if (!response.ok) {
        const err = await response.json();
        setStatus(`Error submitting URL: ${err.detail || response.statusText}`);
        return;
      }

      setStatus(`Successfully submitted URL to pending queue.`);
      setManualUrl('');
      if (isAuthorized) {
        fetchReviews(); // Refresh if authorized
      }
    } catch (e) {
      setStatus('Network error submitting URL.');
    }
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  return (
    <section className="hitl-panel glass-card">
      <h2>Human-in-the-Loop (HITL) Security Review</h2>
      
      <div className="hitl-panel__form-section">
        <h3>Report Suspicious URL</h3>
        <form onSubmit={handleManualSubmit} className="hitl-panel__submit-form">
          <input
            type="text"
            placeholder="https://example-phish.com/login"
            value={manualUrl}
            onChange={e => setManualUrl(e.target.value)}
            required
          />
          <select value={manualLabel} onChange={e => setManualLabel(e.target.value)}>
            <option value="phishing">Phishing</option>
            <option value="suspicious">Suspicious</option>
            <option value="safe">Safe</option>
          </select>
          <button type="submit" className="btn btn-primary">Report URL</button>
        </form>
      </div>

      <div className="hitl-panel__admin-auth">
        <label htmlFor="hitl-admin-key">Admin Access Key</label>
        <input
          id="hitl-admin-key"
          type="password"
          placeholder="Enter X-ADMIN-KEY to review submissions"
          value={adminKey}
          onChange={e => setAdminKey(e.target.value)}
          autoComplete="current-password"
        />
      </div>

      {status && <div className="hitl-panel__status-banner">{status}</div>}

      {isAuthorized && (
        <div className="hitl-panel__dashboard">
          <div className="hitl-panel__pending-section">
            <h3>Pending Submissions ({pendingList.length})</h3>
            {pendingList.length === 0 ? (
              <div className="muted">No pending URLs to review. Excellent work!</div>
            ) : (
              <div className="hitl-table-wrapper">
                <table className="hitl-table">
                  <thead>
                    <tr>
                      <th>Submitted URL</th>
                      <th>User Report</th>
                      <th>Date</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pendingList.map(item => (
                      <tr key={item.id}>
                        <td className="hitl-table__url" title={item.url}>{item.url}</td>
                        <td>
                          <span className={`badge badge--${item.user_label}`}>
                            {item.user_label}
                          </span>
                        </td>
                        <td>{formatDate(item.created_at)}</td>
                        <td className="hitl-table__actions">
                          <button
                            onClick={() => handleResolve(item.url, 'safe')}
                            className="btn btn-safe"
                          >
                            Mark Safe
                          </button>
                          <button
                            onClick={() => handleResolve(item.url, 'suspicious')}
                            className="btn btn-suspicious"
                          >
                            Suspicious
                          </button>
                          <button
                            onClick={() => handleResolve(item.url, 'phishing')}
                            className="btn btn-danger"
                          >
                            Phishing
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="hitl-panel__audit-section">
            <h3>Resolution & Audit Log</h3>
            {auditLogs.length === 0 ? (
              <div className="muted">No resolutions logged yet.</div>
            ) : (
              <div className="hitl-audit-list">
                {auditLogs.map(log => (
                  <div key={log.id} className="hitl-audit-item">
                    <div className="hitl-audit-meta">
                      <span className="hitl-audit-reviewer">{log.reviewer}</span>
                      <span className="hitl-audit-action">{log.action}</span>
                      <span className="hitl-audit-time">{formatDate(log.timestamp)}</span>
                    </div>
                    <div className="hitl-audit-url">{log.url}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
