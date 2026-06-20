/**
 * EnclosureAI — SSE Stream Hook
 * Handles Server-Sent Events consumption from /api/generate.
 * Phase 5 implementation.
 */

import { useCallback, useRef } from 'react'

export default function useSSEStream() {
  const eventSourceRef = useRef(null)

  const connect = useCallback((url, onEvent) => {
    // SSE implementation in Phase 5
    // Will use EventSource or fetch with ReadableStream
    console.log('[useSSEStream] Connection stub — Phase 5 implementation')
  }, [])

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
  }, [])

  return { connect, disconnect }
}
