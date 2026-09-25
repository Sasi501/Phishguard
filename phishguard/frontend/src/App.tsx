import { useState, useEffect, useRef } from 'react'
import useAnalysis from './hooks/useAnalysis'
import type { ScanEntry, AnalyzeRequest } from './types/api'
import { SIZES } from './theme'
import ParticleBackground from './components/ParticleBackground'
import NavigationBar from './components/NavigationBar'
import ScannerPanel from './components/ScannerPanel'
import ThreatMeter from './components/ThreatMeter'
import RiskAssessmentCard from './components/RiskAssessmentCard'
import EnginePanel from './components/EnginePanel'
import EngineSignalCard from './components/EngineSignalCard'
import URLAnatomy from './components/URLAnatomy'
import DomainIntelligence from './components/DomainIntelligence'
import ThreatIntelligence from './components/ThreatIntelligence'
import RedirectAnalysis from './components/RedirectAnalysis'
import XAIPanel from './components/XAIPanel'
import ModelRegistryPanel from './components/ModelRegistryPanel'
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

  // When a new result arrives, prepend to history
  useEffect(() => {
    if (!analysis.result) return
    const entry: ScanEntry = {
      id: crypto.randomUUID(),
      timestamp: new Date(),
      url: lastUrlRef.current,
      result: analysis.result,
    }
    setHistory(prev => [entry, ...prev].slice(0, SIZES.historyMax))
  }, [analysis.result])

  const handleSubmit = (req: AnalyzeRequest) => {
    setActiveEntry(null)
    lastUrlRef.current = req.url
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
        onToggleRegistry={() => setShowRegistry(s => !s)}
        onToggleHITL={() => setShowHITL(s => !s)}
        onToggleSettings={() => setShowSettings(s => !s)}
        isRegistryOpen={showRegistry}
        isHITLOpen={showHITL}
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
                confidence={displayResult.xai ? 100 : undefined}
                url={resultUrl}
              />
              <ThreatMeter
                score={displayResult.ensemble_score_percent}
                riskLevel={displayResult.ensemble_risk_level}
              />
            </div>

            {displayResult.individual_scores_percent &&
              Object.keys(displayResult.individual_scores_percent).length > 0 && (
                <EnginePanel scores={displayResult.individual_scores_percent} />
              )}

            {displayResult.xai && displayResult.xai.engine_signals && displayResult.xai.engine_signals.length > 0 && (
              <section className="engine-signals-section glass-card" aria-labelledby="multimodal-heading">
                <div className="engine-signals-section__header">
                  <h2 id="multimodal-heading" className="engine-signals-section__title">MULTI-MODAL ENGINE SIGNALS</h2>
                  <p>Individual engine evidence; not the final ensemble assessment.</p>
                </div>
                <div className="engine-signals-section__grid">
                  {displayResult.xai.engine_signals.map((signal, index) => (
                    <EngineSignalCard key={`${signal.engine}-${index}`} signal={signal} />
                  ))}
                </div>
              </section>
            )}

            <URLAnatomy url={resultUrl} />
            <DomainIntelligence
              url={displayResult.redirect_analysis?.final_url || resultUrl}
              xai={displayResult.xai ?? null}
            />
            <ThreatIntelligence xai={displayResult.xai ?? null} />
            <RedirectAnalysis analysis={displayResult.redirect_analysis} />

            {(displayResult.xai_summary || displayResult.xai || (displayResult.reasons && displayResult.reasons.length > 0)) && (
              <XAIPanel
                summary={displayResult.xai_summary}
                reasons={displayResult.reasons ?? []}
                xai={displayResult.xai ?? null}
              />
            )}

            {displayResult.thumbnail_base64 && (
              <div className="app-thumbnail glass-card">
                <h3>Page Thumbnail</h3>
                <img src={`data:image/jpeg;base64,${displayResult.thumbnail_base64}`} alt="Page thumbnail" />
              </div>
            )}
          </div>
        )}
        {history.length > 0 && (
          <ScanHistory entries={history} onSelect={handleHistorySelect} />
        )}
        <EngineStatus />
        {showRegistry && <ModelRegistryPanel />}
        {showHITL && <HITLLabelingPanel />}
        {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
      </main>
      <Footer />
    </>
  )
}

export default App
