import { useEffect, useState } from 'react'
import './ModelRegistryPanel.css'
import Modal from './Modal'
import { useCallback } from 'react'

type ModelList = Record<string, string[]>

export default function ModelRegistryPanel() {
  const [models, setModels] = useState<ModelList>({})
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null)
  const [versions, setVersions] = useState<Array<any>>([])
  const [latestMeta, setLatestMeta] = useState<any | null>(null)
  const [status, setStatus] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/registry/models/')
      .then(r => r.json())
      .then(setModels)
      .catch(() => setModels({}))
  }, [])

  const loadVersions = (name: string) => {
    setSelectedModel(name)
    setSelectedVersion(null)
    // mark model as seen in localStorage so NEW badge is dismissed after user interacts
    try {
      const seenRaw = localStorage.getItem('seenModels')
      const seen = seenRaw ? JSON.parse(seenRaw) : {}
      seen[name] = true
      localStorage.setItem('seenModels', JSON.stringify(seen))
    } catch (e) { /* ignore */ }

    fetch(`/api/registry/models/${name}/versions`)
      .then(r => r.json())
      .then(data => {
        setVersions(data.versions || [])
        if ((data.versions || []).length > 0) {
          setSelectedVersion(data.versions[0].version)
          setLatestMeta(data.versions[0].metadata)
        } else {
          setLatestMeta(null)
        }
      })
      .catch(() => { setVersions([]); setLatestMeta(null) })
  }

  const onVersionChange = (ver: string) => {
    setSelectedVersion(ver)
    const v = versions.find(x => x.version === ver)
    setLatestMeta(v ? v.metadata : null)
  }

  const [showModal, setShowModal] = useState(false)
  const [modalMsg, setModalMsg] = useState('')
  const [adminKey, setAdminKey] = useState<string>('');

  const onPromoteConfirm = useCallback(async () => {
    if (!selectedModel || !selectedVersion) return
    if (!adminKey) {
      setStatus('⚠️ Please enter your Admin Key above before promoting.')
      setShowModal(false)
      return
    }
    setShowModal(false)
    setStatus('Promoting...')
    const form = new FormData()
    form.append('name', selectedModel)
    form.append('version', selectedVersion)
    const headers: Record<string,string> = {}
    if (adminKey) headers['X-ADMIN-KEY'] = adminKey
    const resp = await fetch('/api/registry/promote', { method: 'POST', body: form, headers })
    if (!resp.ok) {
      try {
        const err = await resp.json()
        if (resp.status === 403) {
          setStatus('🔒 Access denied. Check your Admin Key and try again.')
        } else {
          setStatus(`Error promoting: ${err.detail || resp.status}`)
        }
      } catch { setStatus('Error promoting') }
      return
    }
    const j = await resp.json()
    setStatus(`✅ Promoted to ${j.promoted_to}`)
  }, [selectedModel, selectedVersion, adminKey])

  const downloadArtifact = async (name: string, version: string) => {
    if (!name || !version) return
    if (!adminKey) {
      setStatus('⚠️ Please enter your Admin Key above before downloading.')
      return
    }
    setStatus('Downloading...')
    try {
      const headers: Record<string, string> = {}
      if (adminKey) headers['X-ADMIN-KEY'] = adminKey
      const resp = await fetch(`/api/registry/models/${encodeURIComponent(name)}/versions/${encodeURIComponent(version)}/artifact`, { headers })
      if (!resp.ok) {
        if (resp.status === 403) {
          setStatus('🔒 Access denied. Check your Admin Key and try again.')
        } else {
          setStatus(`Download failed: ${resp.status}`)
        }
        return
      }
      const blob = await resp.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      const contentDisp = resp.headers.get('content-disposition')
      let filename = `${name}-${version}.bin`
      if (contentDisp) {
        const m = /filename="?([^";]+)"?/.exec(contentDisp)
        if (m) filename = m[1]
      }
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      setStatus('Download complete')
    } catch (e) {
      setStatus('Error downloading artifact')
    }
  }

  const promote = () => {
    if (!selectedModel || !selectedVersion) return
    setModalMsg(`Promote ${selectedModel}@${selectedVersion} as active meta-learner? This will overwrite the currently active model.`)
    setShowModal(true)
  }


  const isNewModel = (name: string) => {
    try {
      const seenRaw = localStorage.getItem('seenModels')
      const seen = seenRaw ? JSON.parse(seenRaw) : {}
      return !seen[name]
    } catch (e) { return false }
  }

  const humanSize = (bytes: number | null) => {
    if (bytes === null || bytes === undefined) return '—'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024*1024) return `${(bytes/1024).toFixed(1)} KB`
    return `${(bytes/(1024*1024)).toFixed(2)} MB`
  }

  return (
    <section className="model-registry glass-card">
      <h2>Model Registry</h2>
      <div className="model-registry__admin-key">
        <label htmlFor="admin-key-input">Admin Key</label>
        <input
          id="admin-key-input"
          type="password"
          placeholder="Enter admin key for promote/download"
          value={adminKey}
          onChange={e => setAdminKey(e.target.value)}
          autoComplete="current-password"
        />
      </div>
      <div className="model-registry__content">
        <div className="model-registry__list">
          <h3>Registered Models</h3>
          {Object.keys(models).length === 0 && <div className="muted">No models registered</div>}
          <ul>
            {Object.keys(models).map(name => (
              <li key={name}>
                <div className="model-list-item">
                  <button onClick={() => loadVersions(name)} className={`link-button ${selectedModel === name ? 'selected' : ''}`}>{name}</button>
                  {isNewModel(name) && <span className="new-badge">NEW</span>}
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="model-registry__details">
          <h3>Versions</h3>
          {!selectedModel && <div className="muted">Select a model to view versions</div>}
          {selectedModel && (
            <div>
              <label htmlFor="versions-select">Choose version:</label>
              <select id="versions-select" value={selectedVersion ?? ''} onChange={e => onVersionChange(e.target.value)}>
                {versions.map(v => (
                  <option key={v.version} value={v.version}>{v.version} — {v.artifact ?? 'artifact'} — {humanSize(v.size)}</option>
                ))}
              </select>

              <h4>Metadata</h4>
              {!latestMeta && <div className="muted">No metadata available for this version</div>}
              {latestMeta && (
                <div>
                  <pre className="meta-block">{JSON.stringify(latestMeta, null, 2)}</pre>
                    <div style={{display: 'flex', gap: 8, alignItems: 'center'}}>
                      <button onClick={promote} className="promote-btn">Promote as active</button>
                      <button onClick={() => downloadArtifact(selectedModel!, selectedVersion!)} className="download-btn">Download Artifact</button>
                    </div>
                    {status && <div className="status">{status}</div>}
                  </div>
              )}

              {showModal && (
                <Modal
                  title="Confirm Promotion"
                  message={modalMsg}
                  onConfirm={onPromoteConfirm}
                  onCancel={() => setShowModal(false)}
                  confirmLabel="Promote"
                  cancelLabel="Cancel"
                />
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
