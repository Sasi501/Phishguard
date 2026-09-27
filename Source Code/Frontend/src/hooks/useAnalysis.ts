import { useState } from 'react'
import type { AnalyzeRequest, AnalyzeResponse, UseAnalysisState } from '../types/api'
import { normalizeAnalyzeResponse } from './analysisResponse'

const API_URL = '/api/analyze-ensemble/'

const NETWORK_ERROR_MSG =
  'Unable to reach the analysis server. Check your connection and try again.'

interface State {
  loading: boolean
  result: AnalyzeResponse | null
  error: string | null
}

const INITIAL_STATE: State = {
  loading: false,
  result: null,
  error: null,
}

export default function useAnalysis(): UseAnalysisState {
  const [state, setState] = useState<State>(INITIAL_STATE)

  const analyze = async (req: AnalyzeRequest): Promise<void> => {
    setState({ loading: true, result: null, error: null })

    const formData = new FormData()
    formData.append('url', req.url)
    if (req.text)  formData.append('text', req.text)
    if (req.image) formData.append('image', req.image)

    // AbortController for 60-second timeout (Gemini LLM can take up to ~30s)
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 60_000)

    try {
      const resp = await fetch(API_URL, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      })
      clearTimeout(timer)

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        throw new Error((err as Record<string, string>).detail ?? `Server error ${resp.status}`)
      }

      const payload: unknown = await resp.json()
      const data = normalizeAnalyzeResponse(payload)
      if (!data) throw new Error('Analysis server returned an invalid response.')

      setState({ loading: false, result: data, error: null })
    } catch (e: unknown) {
      clearTimeout(timer)

      // Classify as network error if AbortError or fetch TypeError
      const isNetwork =
        (e instanceof DOMException && e.name === 'AbortError') ||
        (e instanceof TypeError && e.message.toLowerCase().includes('fetch'))

      const message = isNetwork
        ? NETWORK_ERROR_MSG
        : (e instanceof Error ? e.message : 'Unexpected error')

      setState({ loading: false, result: null, error: message })
    }
  }

  const reset = (): void => setState(INITIAL_STATE)

  return { ...state, analyze, reset }
}
