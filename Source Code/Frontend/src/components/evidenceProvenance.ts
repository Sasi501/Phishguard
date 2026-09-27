/** Labels the exact input represented by a structured engine signal. */
export function inputLabel(source: unknown, scope: unknown): string {
  const normalizedScope = typeof scope === 'string' ? scope : ''

  if (source === 'url_ml') return 'Submitted/original URL'
  if (source === 'nlp') return normalizedScope === 'not_submitted' ? 'No text submitted' : 'Submitted text'
  if (source === 'vision') {
    if (normalizedScope === 'not_submitted') return 'No image submitted'
    if (normalizedScope === 'captured_screenshot') return 'Server-captured screenshot'
    if (normalizedScope === 'not_collected') return 'No screenshot collected'
    return 'Submitted image'
  }
  if (source === 'domain_intelligence') {
    return normalizedScope === 'not_collected' ? 'No domain URL collected' : 'Final resolved URL'
  }
  if (source === 'threat_intelligence') {
    if (normalizedScope === 'original_url') return 'Submitted/original URL'
    if (normalizedScope === 'not_collected') return 'No threat-intelligence URL collected'
    return 'Final resolved URL'
  }
  if (source === 'redirect') return 'Original → intermediate → final URLs'
  return 'Input not reported'
}
