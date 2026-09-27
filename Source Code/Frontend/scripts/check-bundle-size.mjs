/**
 * Bundle size check script.
 * Fails with exit code 1 if non-vendor JS chunks exceed 150 KB gzipped.
 *
 * Usage: node scripts/check-bundle-size.mjs
 * Run after `vite build` to check the dist/ output.
 */

import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { gzipSync } from 'node:zlib'

const LIMIT_BYTES = 150 * 1024  // 150 KB gzipped
const DIST_DIR = new URL('../dist/assets', import.meta.url).pathname.replace(/^\/([A-Z]:)/, '$1')

let totalGzippedBytes = 0
const files = []

let assets
try {
  assets = readdirSync(DIST_DIR)
} catch {
  console.error(`[check-bundle-size] dist/assets/ not found. Run "vite build" first.`)
  process.exit(1)
}

for (const file of assets) {
  // Only check JS files that are NOT vendor chunks
  if (!file.endsWith('.js') || file.startsWith('vendor-')) continue

  const filePath = join(DIST_DIR, file)
  const raw = readFileSync(filePath)
  const gzipped = gzipSync(raw, { level: 9 })
  totalGzippedBytes += gzipped.byteLength
  files.push({ file, raw: raw.byteLength, gzipped: gzipped.byteLength })
}

console.log('\n[check-bundle-size] App chunk analysis (gzipped):')
for (const { file, raw, gzipped } of files) {
  const kb = (gzipped / 1024).toFixed(1)
  const rawKb = (raw / 1024).toFixed(1)
  console.log(`  ${file}: ${kb} KB gzipped (${rawKb} KB raw)`)
}

const totalKb = (totalGzippedBytes / 1024).toFixed(1)
console.log(`\n  Total app chunks: ${totalKb} KB gzipped`)
console.log(`  Limit:            ${(LIMIT_BYTES / 1024).toFixed(0)} KB gzipped\n`)

if (totalGzippedBytes > LIMIT_BYTES) {
  console.error(`[check-bundle-size] ❌ FAIL: App chunks (${totalKb} KB) exceed the 150 KB gzipped limit.`)
  process.exit(1)
} else {
  console.log(`[check-bundle-size] ✅ PASS: App chunks (${totalKb} KB) are within the 150 KB gzipped limit.`)
  process.exit(0)
}
