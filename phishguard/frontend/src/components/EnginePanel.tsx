import { DURATIONS } from '../theme'
import './EnginePanel.css'

interface EnginePanelProps {
  scores: Record<string, number>
}

function getBarColor(score: number): string {
  if (score < 30) return 'var(--color-neon-green)'
  if (score < 70) return 'var(--color-neon-amber)'
  return 'var(--color-neon-crimson)'
}

export default function EnginePanel({ scores }: EnginePanelProps) {
  if (!scores || Object.keys(scores).length === 0) return null

  const entries = Object.entries(scores)

  return (
    <section className="engine-panel glass-card" aria-label="Individual engine signals, separate from the final ensemble score">
      <h2 className="engine-panel__title">INDIVIDUAL ENGINE SIGNALS</h2>
      <div className="engine-panel__grid">
        {entries.map(([engine, score], index) => {
          const rounded = Math.round(score)
          const color = getBarColor(rounded)
          const scale = Math.max(0, Math.min(1, score / 100))
          const delay = index * DURATIONS.barStagger

          return (
            <div key={engine} className="engine-widget">
              <div className="engine-widget__header">
                <span className="engine-widget__name">{engine}</span>
                <span className="engine-widget__score" style={{ color }}>{rounded}%</span>
              </div>
              <div
                className="engine-widget__bar-track"
                role="meter"
                aria-valuenow={rounded}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${engine} score: ${rounded}%`}
              >
                <div
                  className="engine-widget__bar-fill"
                  style={{
                    '--target-scale': scale,
                    '--delay': `${delay}ms`,
                    '--bar-color': color,
                  } as React.CSSProperties}
                />
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
