import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import useAnalysis from './hooks/useAnalysis'
import type { ScanEntry, AnalyzeRequest } from './types/api'
import { SIZES } from './theme'
import ParticleBackground from './components/ParticleBackground'
import NavigationBar from './components/NavigationBar'
import ScannerPanel from './components/ScannerPanel'
import ThreatMeter from './components/ThreatMeter'
import EnginePanel from './components/EnginePanel'
import XAIPanel from './components/XAIPanel'
import ModelRegistryPanel from './components/ModelRegistryPanel'
import ScanHistory from './components/ScanHistory'
import ErrorBanner from './components/ErrorBanner'
import HITLLabelingPanel from './components/HITLLabelingPanel'
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
  const [showRegistry, setShowRegistry] = useState(false)
  const [showHITL, setShowHITL] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showScanner, setShowScanner] = useState(false)

  // Use translation hook to force re-renders on lang change
  const { t } = useTranslation()

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
            <ThreatMeter
              score={displayResult.ensemble_score_percent}
              riskLevel={displayResult.ensemble_risk_level}
            />
            {displayResult.individual_scores_percent &&
              Object.keys(displayResult.individual_scores_percent).length > 0 && (
                <EnginePanel scores={displayResult.individual_scores_percent} />
              )}
            {(displayResult.xai_summary || (displayResult.reasons && displayResult.reasons.length > 0)) && (
              <XAIPanel
                summary={displayResult.xai_summary}
                reasons={displayResult.reasons ?? []}
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
        {showRegistry && <ModelRegistryPanel />}
        {showHITL && <HITLLabelingPanel />}
        {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
      </main>
      <Footer />
    </>
  )
}

export default App
