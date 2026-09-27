import './ModelEvaluationCenter.css'

type Metric = {
  label: string
  value: string
}

const urlMetrics: Metric[] = [
  { label: 'Accuracy', value: '97.90%' },
  { label: 'Precision', value: '98.80%' },
  { label: 'Recall', value: '96.99%' },
  { label: 'F1 score', value: '97.89%' },
  { label: 'ROC-AUC', value: '99.63%' },
]

const featureImportance = [
  ['path_length', '67.2097'],
  ['url_length', '7.4374'],
  ['num_dots', '5.5677'],
  ['num_digits_in_domain', '5.3637'],
  ['hostname_length', '4.8231'],
  ['num_hyphens', '3.1609'],
]

const evaluationSources = [
  'backend/ml/models/metrics.json',
  'backend/ml/train_model.py',
  'backend/ml/models/reproducibility_report.json',
]

export default function ModelEvaluationCenter() {
  return (
    <section className="model-evaluation glass-card" aria-labelledby="model-evaluation-heading">
      <header className="model-evaluation__header">
        <div>
          <p className="model-evaluation__eyebrow">MODEL ANALYTICS</p>
          <h2 id="model-evaluation-heading">MODEL EVALUATION CENTER</h2>
          <p className="model-evaluation__intro">
            Verified offline evaluation evidence for the models and pipelines currently documented in this repository.
          </p>
        </div>
        <span className="model-evaluation__badge">Repository evidence</span>
      </header>

      <div className="model-evaluation__notice" role="note">
        These are held-out URL ML evaluation results, not live scan accuracy and not a measurement of the complete ensemble.
      </div>

      <div className="model-evaluation__grid">
        <article className="model-evaluation__card model-evaluation__card--wide">
          <div className="model-evaluation__card-heading">
            <div>
              <p className="model-evaluation__label">VALIDATED MODEL</p>
              <h3>URL Intelligence · CatBoost</h3>
            </div>
            <span className="model-evaluation__status">IMPLEMENTED + EVALUATED</span>
          </div>
          <div className="model-evaluation__metrics">
            {urlMetrics.map(metric => (
              <div className="model-evaluation__metric" key={metric.label}>
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
              </div>
            ))}
          </div>
          <dl className="model-evaluation__facts">
            <div><dt>Dataset split</dt><dd>80% train / 20% test</dd></div>
            <div><dt>Training samples</dt><dd>79,996</dd></div>
            <div><dt>Held-out test samples</dt><dd>20,000</dd></div>
            <div><dt>Evaluation method</dt><dd>Classification report + ROC-AUC</dd></div>
          </dl>
        </article>

        <article className="model-evaluation__card">
          <p className="model-evaluation__label">REPRODUCIBILITY</p>
          <h3>Deterministic training check</h3>
          <p className="model-evaluation__result">PASS</p>
          <dl className="model-evaluation__facts model-evaluation__facts--stacked">
            <div><dt>Random seed</dt><dd>1337</dd></div>
            <div><dt>Max prediction difference</dt><dd>0.0</dd></div>
            <div><dt>Max importance difference</dt><dd>0.0</dd></div>
          </dl>
          <p className="model-evaluation__muted">
            The repository verifier compares two deterministic CatBoost runs on a 1,000-item reproducibility sample.
          </p>
        </article>

        <article className="model-evaluation__card">
          <p className="model-evaluation__label">FEATURE EVIDENCE</p>
          <h3>Top CatBoost importances</h3>
          <ol className="model-evaluation__importance">
            {featureImportance.map(([feature, value], index) => (
              <li key={feature}>
                <span><b>{index + 1}</b>{feature}</span>
                <strong>{value}</strong>
              </li>
            ))}
          </ol>
          <p className="model-evaluation__muted">Raw feature-importance values from the saved evaluation artifact; not percentages.</p>
        </article>
      </div>

      <section className="model-evaluation__coverage" aria-labelledby="evaluation-coverage-heading">
        <div>
          <p className="model-evaluation__label">EVALUATION COVERAGE</p>
          <h3 id="evaluation-coverage-heading">What is and is not measured</h3>
        </div>
        <div className="model-evaluation__coverage-list">
          <div><span className="model-evaluation__dot model-evaluation__dot--verified" />URL ML / CatBoost <strong>Held-out metrics available</strong></div>
          <div><span className="model-evaluation__dot model-evaluation__dot--pending" />NLP / DistilBERT <strong>Evaluation artifact unavailable</strong></div>
          <div><span className="model-evaluation__dot model-evaluation__dot--pending" />Vision / EfficientNet-B3 <strong>Evaluation artifact unavailable</strong></div>
          <div><span className="model-evaluation__dot model-evaluation__dot--pending" />Fusion / ensemble <strong>No held-out calibration metrics documented</strong></div>
        </div>
      </section>

      <footer className="model-evaluation__footer">
        <div>
          <p className="model-evaluation__label">SOURCE TRACEABILITY</p>
          <p>{evaluationSources.join(' · ')}</p>
        </div>
        <p className="model-evaluation__muted">Runtime scans demonstrate system behavior; they do not replace experimental evaluation.</p>
      </footer>
    </section>
  )
}
