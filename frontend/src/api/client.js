/**
 * EnclosureAI — API Client
 * Axios-based HTTP client for FastAPI backend communication.
 */

import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const client = axios.create({
  baseURL: API_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Health check
 */
export async function checkHealth() {
  const { data } = await client.get('/health')
  return data
}

/**
 * Generate enclosure — returns SSE stream URL info
 * Actual SSE consumption handled by useGeneration hook.
 */
export async function generateEnclosure(request) {
  const { data } = await client.post('/api/generate', request)
  return data
}

/**
 * Download generated ZIP
 */
export function getDownloadUrl(jobId) {
  return `${API_URL}/api/download/${jobId}`
}

/**
 * Get preview STL URL for Three.js
 */
export function getPreviewSTLUrl(jobId, part = 'body') {
  return `${API_URL}/api/preview/${jobId}/${part}.stl`
}

/**
 * Get thermal report
 */
export async function getThermalReport(jobId) {
  const { data } = await client.get(`/api/thermal/${jobId}`)
  return data
}

/**
 * Predict strategy based on design context (Phase 8)
 */
export async function predictStrategy(designContext) {
  const params = new URLSearchParams({
    use_case: designContext.use_case || 'BENCH_PROTOTYPE',
    access_frequency: designContext.access_frequency || 'RARELY',
    mounting: designContext.mounting || 'DESKTOP',
    environment: designContext.environment || 'INDOOR',
    total_wattage: designContext.total_wattage || '0',
  })
  const { data } = await client.get(`/api/predict-strategy?${params}`)
  return data
}

export default client
