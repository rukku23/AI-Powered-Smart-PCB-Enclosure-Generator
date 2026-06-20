/**
 * EnclosureAI — useGeneration Hook
 * Manages SSE streaming from POST /api/generate endpoint.
 * Tracks generation lifecycle: idle → generating → rendering → complete/error
 */
import { useState, useCallback, useRef } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const INITIAL_STATE = {
  status: 'idle',       // idle | validating | generating | rendering | correcting | complete | error
  jobId: null,
  reasoning: '',
  thermalReport: null,
  constraints: null,
  dfmResult: null,
  error: null,
  attempt: 0,
  renderTime: 0,
  strategy: null,
  strategyReason: null,
}

export default function useGeneration() {
  const [state, setState] = useState(INITIAL_STATE)
  const abortRef = useRef(null)

  const generate = useCallback(async (formData) => {
    // Reset state
    setState({ ...INITIAL_STATE, status: 'validating' })

    // Build request body
    const body = {
      pcb: {
        length: parseFloat(formData.pcb.length),
        width: parseFloat(formData.pcb.width),
        thickness: parseFloat(formData.pcb.thickness) || 1.6,
        mounting_hole_diameter: parseFloat(formData.pcb.mounting_hole_diameter) || 3.2,
      },
      components: (formData.components || []).map(c => ({
        component_type: c.type || 'GENERIC',
        label: c.label || 'Component',
        position_x: parseFloat(c.position_x) || 0,
        position_y: parseFloat(c.position_y) || 0,
        height: parseFloat(c.height) || 5,
        wattage: parseFloat(c.wattage) || 0,
        face_access: c.face_access || 'NONE',
        connector_width: parseFloat(c.connector_width) || null,
        connector_height: parseFloat(c.connector_height) || null,
      })),
      material: formData.material || 'PETG',
      print_technology: formData.print_technology || 'FDM',
      lid_style: formData.lid_style || 'SNAP_FIT',
      ventilation: formData.ventilation !== false,
      display_window: formData.display_window || false,
      aesthetic_style: formData.aesthetic_style || 'MINIMAL',
    }

    if (formData.preset) {
      body.preset = formData.preset
    }

    if (formData.design_context) {
      body.design_context = formData.design_context
    }

    try {
      // Create abort controller
      const abort = new AbortController()
      abortRef.current = abort

      // POST with fetch for SSE support
      const response = await fetch(`${API_URL}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: abort.signal,
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Request failed' }))
        throw new Error(err.detail || err.message || `HTTP ${response.status}`)
      }

      // Read SSE stream
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Parse SSE lines
        const lines = buffer.split('\n\n')
        buffer = lines.pop() // keep incomplete chunk

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            handleSSEEvent(event, setState)
          } catch (e) {
            // Skip malformed events
          }
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') return
      setState(prev => ({
        ...prev,
        status: 'error',
        error: err.message || 'Generation failed',
      }))
    }
  }, [])

  const reset = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
    setState(INITIAL_STATE)
  }, [])

  return { state, generate, reset }
}

function handleSSEEvent(event, setState) {
  switch (event.event) {
    case 'validating':
      setState(prev => ({ ...prev, status: 'validating', jobId: event.job_id }))
      break

    case 'constraints_computed':
      setState(prev => ({
        ...prev,
        constraints: event,
      }))
      break

    case 'dfm_result':
      setState(prev => ({
        ...prev,
        dfmResult: event,
        ...(event.passed === false ? { status: 'error', error: 'DFM validation failed' } : {}),
      }))
      break

    case 'thermal_computed':
      setState(prev => ({
        ...prev,
        thermalReport: event.thermal ? {
            thermal_health_score:   event.thermal.thermal_health_score,
            verdict:                event.thermal.verdict,
            slot_count:             event.thermal.slot_count,
            vent_face:              event.thermal.vent_face,
            required_area_cm2:      event.thermal.required_area_cm2,
            implemented_area_cm2:   event.thermal.implemented_area_cm2,
            passive_cooling_ok:     event.thermal.passive_cooling_ok,
            recommendation:         event.thermal.recommendation,
            chimney_needed:         event.thermal.chimney_needed,
        } : null,
      }))
      break

    case 'generating':
      setState(prev => ({
        ...prev,
        status: 'generating',
        attempt: event.attempt || 1,
      }))
      break

    case 'strategy_selected':
      setState(prev => ({
        ...prev,
        strategy: event.strategy || null,
        strategyReason: event.reason || null,
      }))
      break

    case 'reasoning_chunk':
      setState(prev => ({
        ...prev,
        reasoning: prev.reasoning + (event.data || ''),
      }))
      break

    case 'rendering':
      setState(prev => ({
        ...prev,
        status: 'rendering',
        attempt: event.attempt || prev.attempt,
      }))
      break

    case 'correction':
      setState(prev => ({
        ...prev,
        status: 'correcting',
        attempt: event.attempt || prev.attempt,
        error: event.error || 'Self-correcting...',
      }))
      break

    case 'complete':
      setState(prev => ({
        ...prev,
        status: 'complete',
        jobId: event.job_id,
        reasoning: event.reasoning || prev.reasoning,
        thermalReport: event.thermal || prev.thermalReport,
        renderTime: event.render_time_ms || 0,
        attempt: event.attempts || prev.attempt,
        strategy: event.strategy || prev.strategy,
        error: null,
      }))
      break

    case 'error':
      setState(prev => ({
        ...prev,
        status: 'error',
        error: event.message || 'Unknown error',
      }))
      break
  }
}
