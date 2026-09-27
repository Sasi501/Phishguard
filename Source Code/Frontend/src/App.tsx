import { useState, useEffect, useRef } from 'react'
import useAnalysis from './hooks/useAnalysis'
import type { ScanEntry, AnalyzeRequest } from './types/api'
import { SIZES } from './theme'
import ParticleBackground from './components/ParticleBackground'
import NavigationBar from './components/NavigationBar'
import ScannerPanel from './components/ScannerPanel'
import ThreatMeter from './components/ThreatMeter'
import RiskAssessmentCard from './components/RiskAssessmentCard'
import BasicDetectionSummary from './components/BasicDetectionSummary'
import URLAnatomy from './components/URLAnatomy'
import XAIPanel from './components/XAIPanel'
import EngineSignalCard from './components/EngineSignalCard'
import ModelRegistryPanel from './components/ModelRegistryPanel'
import ModelEvaluationCenter from './components/ModelEvaluationCenter'
import EvidenceMatrix from './components/EvidenceMatrix'
import ScanAnalytics from './components/ScanAnalytics'
import ScanHistory from './components/ScanHistory'
import ErrorBanner from './components/ErrorBanner'
import HITLLabelingPanel from './components/HITLLabelingPanel'
import EngineStatus from './components/EngineStatus'
import HeroDashboard from './components/HeroDashboard'
import SettingsPanel from './components/SettingsPanel'
import Footer from './components/Footer'
import './App.css'

function App() {
  const analysis = useAnalysis()
  const [history, setHistory] = useState<ScanEntry[]>([])
  const [activeEntry, setActiveEntry] = useState<ScanEntry | null>(null)
  const lastUrlRef = useRef<string>('')
  const lastInputRef = useRef({ hasText: false, hasImage: false })
  const [latestResultAt, setLatestResultAt] = useState<Date | null>(null)
  const [viewMode, setViewMode] = useState<'basic' | 'advanced'>('basic')

  // When a new result arrives, prepend to history
  useEffect(() => {
    if (!analysis.result) return
    const timestamp = new Date()
    const entry: ScanEntry = {
      id: crypto.randomUUID(),
      timestamp,
      url: lastUrlRef.current,
      result: analysis.result,
      ...lastInputRef.current,
    }
    setLatestResultAt(timestamp)
    setHistory(prev => [entry, ...prev].slice(0, SIZES.historyMax))
  }, [analysis.result])

  const handleSubmit = (req: AnalyzeRequest) => {
    setActiveEntry(null)
    lastUrlRef.current = req.url
    lastInputRef.current = { hasText: Boolean(req.text?.trim()), hasImage: Boolean(req.image) }
    analysis.analyze(req)
  }

  const handleHistorySelect = (entry: ScanEntry) => {
    setActiveEntry(entry)
  }

  const displayResult = activeEntry?.result ?? analysis.result
  const resultUrl = activeEntry?.url ?? lastUrlRef.current
  const [showRegistry, setShowRegistry] = useState(false)
  const [showHITL, setShowHITL] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showEvaluation, setShowEvaluation] = useState(false)
  const [showAnalytics, setShowAnalytics] = useState(false)
  const [showScanner, setShowScanner] = useState(false)

  // Back to dashboard handler
  const handleBackToDashboard = () => {
    setShowScanner(false)
    setActiveEntry(null)
    analysis.reset()
  }

  return (
    <>
      <ParticleBackground />
      <NavigationBar
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onToggleRegistry={() => setShowRegistry(s => !s)}
        onToggleHITL={() => setShowHITL(s => !s)}
        onToggleSettings={() => setShowSettings(s => !s)}
        onToggleEvaluation={() => setShowEvaluation(s => !s)}
        onToggleAnalytics={() => setShowAnalytics(s => !s)}
        isRegistryOpen={showRegistry}
        isHITLOpen={showHITL}
        isEvaluationOpen={showEvaluation}
        isAnalyticsOpen={showAnalytics}
      />
      <main className="app-main">
        {analysis.error && !activeEntry && (
          <ErrorBanner message={analysis.error} onDismiss={analysis.reset} />
        )}

        {!showScanner && !displayResult && !analysis.loading ? (
          <HeroDashboard onStartScan={() => setShowScanner(true)} />
        ) : (
          <div className="app-scanner-wrapper">
            <ScannerPanel loading={analysis.loading} onSubmit={handleSubmit} />
            {!analysis.loading && (
              <button className="app-back-btn" onClick={handleBackToDashboard} type="button">
                ← Back to Dashboard
              </button>
            )}
          </div>
        )}

        {displayResult && (
          <div className="app-results">
            <div className="app-results__overview">
              <RiskAssessmentCard
                score={displayResult.ensemble_score_percent}
                riskLevel={displayResult.ensemble_risk_level}
                url={resultUrl}
              />
              <ThreatMeter
                score={displayResult.ensemble_score_percent}
                riskLevel={displayResult.ensemble_risk_level}
              />
            </div>

            {viewMode === 'basic' ? (
              <BasicDetectionSummary
                result={displayResult}
                onViewDetails={() => setViewMode('advanced')}
              />
            ) : (
              <>
                {displayResult.xai?.engine_signals && (
                  <section className="engine-signals-section glass-card" aria-labelledby="engine-signals-heading">
                    <header className="engine-signals-section__header">
                      <h2 id="engine-signals-heading" className="engine-signals-section__title">Individual Engine Signals</h2>
                      <p>Each signal is an individual evidence input, not the final ensemble score.</p>
                    </header>
                    <div className="engine-signals-section__grid">
                      {displayResult.xai.engine_signals
                        .filter(signal => signal.score_type === 'engine_signal')
                        .map((signal, index) => (
                          <EngineSignalCard key={`${signal.source ?? signal.engine}-${index}`} signal={signal} />
                        ))}
                    </div>
                  </section>
                )}

                <URLAnatomy url={resultUrl} />
                <XAIPanel
                  summary={displayResult.xai_summary}
                  reasons={displayResult.reasons ?? []}
                  xai={displayResult.xai ?? null}
                  ensembleScore={displayResult.ensemble_score_percent}
                  ensembleRiskLevel={displayResult.ensemble_risk_level}
                  submittedUrl={resultUrl}
                  receivedAt={activeEntry?.timestamp ?? latestResultAt ?? undefined}
                  submittedText={activeEntry ? activeEntry.hasText ?? false : lastInputRef.current.hasText}
                  submittedImage={activeEntry ? activeEntry.hasImage ?? false : lastInputRef.current.hasImage}
                  analysisStatus={displayResult.analysis_status}
                  engineStatus={displayResult.engine_status}
                />
                <EvidenceMatrix result={displayResult} />

                {displayResult.thumbnail_base64 && (
                  <div className="app-thumbnail glass-card">
                    <h3>Page Thumbnail</h3>
                    <img src={`data:image/jpeg;base64,${displayResult.thumbnail_base64}`} alt="Page thumbnail" />
                  </div>
                )}
              </>
            )}
          </div>
        )}
        {history.length > 0 && (
          <ScanHistory entries={history} onSelect={handleHistorySelect} />
        )}
        {viewMode === 'advanced' && <EngineStatus />}
        {showAnalytics && <ScanAnalytics entries={history} />}
        {showEvaluation && <ModelEvaluationCenter />}
        {showRegistry && <ModelRegistryPanel />}
        {showHITL && <HITLLabelingPanel />}
        {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
      </main>
      <Footer />
    </>
  )
}

export default App
