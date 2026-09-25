import React, { useState, useEffect, useCallback } from 'react';
import type { AnalyzeResponse } from '../types/api';
import './HITLLabelingPanel.css';

interface PendingItem {
  id?: number;
  case_id: string;
  url: string;
  user_label: string;
  status: string;
  case_status?: string;
  created_at: number;
  reviewer?: string | null;
  review_timestamp?: number | null;
  analyst_comment?: string | null;
  evidence_snapshot?: EvidenceSnapshot | null;
}

interface EvidenceSnapshot {
  captured_at?: number;
  source?: string;
  original_url?: string;
  final_url?: string;
  ensemble_score?: number;
  ensemble_risk_level?: string;
  engine_signals?: NonNullable<AnalyzeResponse['xai']>['engine_signals'];
  xai?: AnalyzeResponse['xai'];
  domain_intelligence?: unknown;
  threat_intelligence?: unknown;
  redirect_analysis?: AnalyzeResponse['redirect_analysis'];
}

interface AuditLog {
  id?: number;
  case_id?: string;
  url: string;
  action: string;
  reviewer?: string | null;
  timestamp: number;
  comment?: string;
}

export default function HITLLabelingPanel() {
  const [pendingList, setPendingList] = useState<PendingItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [adminKey, setAdminKey] = useState<string>('');
  const [manualUrl, setManualUrl] = useState<string>('');
  const [manualLabel, setManualLabel] = useState<string>('phishing');
  const [status, setStatus] = useState<string | null>(null);
  const [isAuthorized, setIsAuthorized] = useState<boolean>(false);
  const [selectedUrl, setSelectedUrl] = useState<string | null>(null);
  const [caseEvidence, setCaseEvidence] = useState<AnalyzeResponse | null>(null);
  const [caseLoading, setCaseLoading] = useState<boolean>(false);
  const [caseError, setCaseError] = useState<string | null>(null);
  const [analystComment, setAnalystComment] = useState<string>('');
  const [evidenceSource, setEvidenceSource] = useState<'snapshot' | 'live' | null>(null);

  const fetchReviews = useCallback(async () => {
    if (!adminKey) {
      setPendingList([]);
      setAuditLogs([]);
      setIsAuthorized(false);
      setSelectedUrl(null);
      setCaseEvidence(null);
      setCaseError(null);
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
        setSelectedUrl(null);
        setCaseEvidence(null);
        setCaseError(null);
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
      setSelectedUrl(null);
      setCaseEvidence(null);
      setCaseError(null);
      setStatus('Failed to query HITL endpoints.');
    }
  }, [adminKey]);

  const loadCaseEvidence = useCallback(async (item: PendingItem) => {
    const url = item.url;
    setSelectedUrl(url);
    setCaseLoading(true);
    setCaseError(null);
    setCaseEvidence(null);
    setEvidenceSource(null);

    if (item.evidence_snapshot) {
      const snapshot = item.evidence_snapshot;
      setCaseEvidence({
        ensemble_risk_level: (snapshot.ensemble_risk_level || 'unavailable') as AnalyzeResponse['ensemble_risk_level'],
        ensemble_score_percent: snapshot.ensemble_score ?? 0,
        xai_summary: snapshot.xai?.summary || '',
        xai: snapshot.xai,
        individual_scores_percent: {},
        reasons: [],
        redirect_analysis: snapshot.redirect_analysis,
      });
      setEvidenceSource('snapshot');
      setCaseLoading(false);
      return;
    }

    try {
      const form = new FormData();
      form.append('url', url);

      const response = await fetch('/api/analyze-ensemble/', {
        method: 'POST',
        body: form,
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        setCaseError((err as Record<string, string>).detail ?? 'Scan evidence unavailable for this URL.');
        return;
      }

      const data: AnalyzeResponse = await response.json();
      setCaseEvidence(data);
      setEvidenceSource('live');
    } catch (e) {
      setCaseError('Unable to load current AI scan evidence for this URL.');
    } finally {
      setCaseLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (adminKey) {
        fetchReviews();
      }
    }, 500); // Debounce key typing
    return () => clearTimeout(timer);
  }, [adminKey, fetchReviews]);

  const handleClaim = async (url: string) => {
    setStatus('Claiming case for review...');
    try {
      const form = new FormData();
      form.append('url', url);
      form.append('reviewer', 'admin');
      const response = await fetch('/api/hitl/claim/', {
        method: 'POST',
        headers: { 'X-ADMIN-KEY': adminKey },
        body: form,
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        setStatus(`Error claiming case: ${err.detail || response.statusText}`);
        return;
      }
      setStatus('Case moved to under review.');
      fetchReviews();
    } catch (e) {
      setStatus('Network error claiming case.');
    }
  };

  const handleResolve = async (url: string, finalLabel: string) => {
    setStatus(`Resolving URL as ${finalLabel}...`);
    try {
      const form = new FormData();
      form.append('url', url);
      form.append('final_label', finalLabel);
      form.append('reviewer', 'admin');
      if (analystComment.trim()) form.append('comment', analystComment.trim());

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
      setAnalystComment('');
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
      let evidenceSnapshot: EvidenceSnapshot | null = null;
      try {
        const scanForm = new FormData();
        scanForm.append('url', manualUrl);
        const scanResponse = await fetch('/api/analyze-ensemble/', {
          method: 'POST',
          body: scanForm,
        });
        if (scanResponse.ok) {
          const analysis: AnalyzeResponse = await scanResponse.json();
          const redirect = analysis.redirect_analysis;
          evidenceSnapshot = {
            captured_at: Date.now() / 1000,
            source: 'ensemble_analysis',
            original_url: redirect?.original_url || manualUrl,
            final_url: redirect?.final_url || manualUrl,
            ensemble_score: analysis.ensemble_score_percent,
            ensemble_risk_level: analysis.ensemble_risk_level,
            engine_signals: analysis.xai?.engine_signals,
            xai: analysis.xai,
            redirect_analysis: redirect,
          };
        }
      } catch {
        // Submission remains available when optional evidence capture fails.
      }
      const form = new FormData();
      form.append('url', manualUrl);
      form.append('user_label', manualLabel);
      if (evidenceSnapshot) {
        form.append('evidence_snapshot', JSON.stringify(evidenceSnapshot));
      }

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

  const xai = caseEvidence?.xai ?? null;
  const selectedCase = pendingList.find(item => item.url === selectedUrl) ?? null;
  const threatAndDomainSignals = xai?.engine_signals?.filter(signal =>
    /threat|domain/i.test(signal.engine || '')
  ) ?? [];

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
                      <tr
                        key={item.case_id || item.id || item.url}
                        className={selectedUrl === item.url ? 'hitl-table__row hitl-table__row--selected' : 'hitl-table__row'}
                        onClick={() => loadCaseEvidence(item)}
                        style={{ cursor: 'pointer' }}
                      >
                        <td className="hitl-table__url" title={item.url}>{item.url}</td>
                        <td>
                          <span className={`badge badge--${item.case_status || item.status}`}>
                            {item.case_status || item.status}
                          </span>
                        </td>
                        <td>{formatDate(item.created_at)}</td>
                        <td className="hitl-table__actions" onClick={e => e.stopPropagation()}>
                          {(item.status === 'pending' || item.status === 'under_review') && (
                            <button
                              onClick={() => handleClaim(item.url)}
                              className="btn btn-primary"
                              disabled={item.status === 'under_review'}
                            >
                              {item.status === 'under_review' ? 'Under Review' : 'Claim'}
                            </button>
                          )}
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
                          <button
                            onClick={() => handleResolve(item.url, 'needs_investigation')}
                            className="btn btn-primary"
                          >
                            Investigate
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {(selectedUrl || caseEvidence || caseError || caseLoading) && (
            <div className="hitl-panel__case-section">
              <h3>Case Evidence</h3>

              {caseLoading ? (
                <div className="muted">Loading current AI assessment for {selectedUrl}...</div>
              ) : caseError ? (
                <div className="muted">{caseError}</div>
              ) : caseEvidence ? (
                <>
                  <div className="hitl-evidence__info-grid">
                    <div className="hitl-evidence__info-card">
                      <span className="hitl-evidence__label">URL</span>
                      <strong className="hitl-evidence__value hitl-evidence__value--mono">{selectedUrl ?? 'Unavailable'}</strong>
                    </div>
                    <div className="hitl-evidence__info-card">
                      <span className="hitl-evidence__label">Current AI Assessment</span>
                      <strong className="hitl-evidence__value">
                        {caseEvidence.ensemble_risk_level} · {Math.round(caseEvidence.ensemble_score_percent)}%
                      </strong>
                    </div>
                    <div className="hitl-evidence__info-card">
                      <span className="hitl-evidence__label">Evidence Source</span>
                      <strong className="hitl-evidence__value">
                        {evidenceSource === 'snapshot'
                          ? 'Evidence captured at submission'
                          : 'Current live analysis'}
                      </strong>
                    </div>
                    <div className="hitl-evidence__info-card">
                      <span className="hitl-evidence__label">Case Status</span>
                      <strong className="hitl-evidence__value">
                        {selectedCase?.case_status || selectedCase?.status || 'pending'}
                      </strong>
                      {selectedCase?.reviewer && (
                        <span className="hitl-evidence__meta">Reviewer: {selectedCase.reviewer}</span>
                      )}
                      {selectedCase?.review_timestamp && (
                        <span className="hitl-evidence__meta">
                          Reviewed: {formatDate(selectedCase.review_timestamp)}
                        </span>
                      )}
                    </div>
                  </div>

                  {caseEvidence.redirect_analysis && (
                    <div className="hitl-evidence__block">
                      <h4>Redirect Evidence (Supporting Only)</h4>
                      <p className="hitl-evidence__summary">
                        {caseEvidence.redirect_analysis.num_redirects} redirect(s), state:{' '}
                        {caseEvidence.redirect_analysis.resolution_state}
                      </p>
                      <div className="hitl-evidence__meta">
                        Final destination: {caseEvidence.redirect_analysis.final_url || 'Unavailable'}
                        {caseEvidence.redirect_analysis.suspicious_redirects
                          ? ' · Suspicious-chain indicator'
                          : ''}
                      </div>
                    </div>
                  )}

                  <div className="hitl-evidence__blocks">
                    {(caseEvidence.xai_summary || caseEvidence.reasons?.length) && (
                      <div className="hitl-evidence__block">
                        <h4>AI Evidence</h4>
                        {caseEvidence.xai_summary && (
                          <p className="hitl-evidence__summary">{caseEvidence.xai_summary}</p>
                        )}
                        {caseEvidence.reasons?.length > 0 && (
                          <ul className="hitl-evidence__list">
                            {caseEvidence.reasons.map((reason, index) => (
                              <li key={`${reason}-${index}`}>{reason}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}

                    {xai && xai.risk_factors && xai.risk_factors.length > 0 && (
                      <div className="hitl-evidence__block">
                        <h4>Risk Factors</h4>
                        <ul className="hitl-evidence__list">
                          {xai.risk_factors.map((factor, index) => (
                            <li key={`${factor.title}-${index}`}>
                              <strong>{factor.title}</strong>: {factor.description}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {xai && xai.safety_factors && xai.safety_factors.length > 0 && (
                      <div className="hitl-evidence__block">
                        <h4>Safety Factors</h4>
                        <ul className="hitl-evidence__list">
                          {xai.safety_factors.map((factor, index) => (
                            <li key={`${factor.title}-${index}`}>
                              <strong>{factor.title}</strong>: {factor.description}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {xai && xai.engine_signals && xai.engine_signals.length > 0 && (
                      <div className="hitl-evidence__block">
                        <h4>Engine Signals</h4>
                        <div className="hitl-evidence__signal-list">
                          {xai.engine_signals.map((signal, index) => (
                            <div key={`${signal.engine}-${index}`} className="hitl-evidence__signal">
                              <div className="hitl-evidence__signal-head">
                                <span>{signal.engine}</span>
                                <strong>{signal.risk_level}</strong>
                              </div>
                              <div className="hitl-evidence__meter">
                                <span style={{ width: `${Math.min(100, Math.max(0, signal.score))}%` }} />
                              </div>
                              {signal.match_status && <div className="hitl-evidence__meta">{signal.match_status}</div>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {xai && xai.feature_importance && xai.feature_importance.length > 0 && (
                      <div className="hitl-evidence__block">
                        <h4>Feature Importance</h4>
                        <ul className="hitl-evidence__list">
                          {xai.feature_importance.map((feature, index) => (
                            <li key={`${feature.feature}-${index}`}>
                              <strong>{feature.feature}</strong>: impact {feature.impact}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {threatAndDomainSignals.length > 0 && (
                      <div className="hitl-evidence__block">
                        <h4>Threat / Domain Evidence</h4>
                        <div className="hitl-evidence__signal-list">
                          {threatAndDomainSignals.map((signal, index) => (
                            <div key={`${signal.engine}-${index}`} className="hitl-evidence__signal">
                              <div className="hitl-evidence__signal-head">
                                <span>{signal.engine}</span>
                                <strong>{signal.risk_level}</strong>
                              </div>
                              <div className="hitl-evidence__meter">
                                <span style={{ width: `${Math.min(100, Math.max(0, signal.score))}%` }} />
                              </div>
                              {signal.sources && signal.sources.length > 0 && (
                                <div className="hitl-evidence__meta">Sources: {signal.sources.join(', ')}</div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="hitl-evidence__review">
                    <label htmlFor="hitl-analyst-comment">Analyst comment (optional)</label>
                    <textarea
                      id="hitl-analyst-comment"
                      value={analystComment}
                      onChange={e => setAnalystComment(e.target.value)}
                      placeholder="Record the reasoning for this verdict."
                      rows={3}
                    />
                  </div>
                </>
              ) : (
                <div className="muted">No live scan evidence is available for the selected URL.</div>
              )}
            </div>
          )}

          <div className="hitl-panel__audit-section">
            <h3>Resolution & Audit Log</h3>
            {auditLogs.length === 0 ? (
              <div className="muted">No resolutions logged yet.</div>
            ) : (
              <div className="hitl-audit-list">
                {auditLogs.map(log => (
                  <div key={log.id || `${log.timestamp}-${log.url}`} className="hitl-audit-item">
                    <div className="hitl-audit-meta">
                      <span className="hitl-audit-reviewer">{log.reviewer || 'system'}</span>
                      <span className="hitl-audit-action">{log.action}</span>
                      <span className="hitl-audit-time">{formatDate(log.timestamp)}</span>
                    </div>
                    <div className="hitl-audit-url">{log.url}</div>
                    {log.comment && <div className="hitl-audit-url">Comment: {log.comment}</div>}
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
