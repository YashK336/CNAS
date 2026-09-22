import { useCallback, useEffect, useRef, useState } from 'react'

import { fetchServiceInfo, isAbortError, toErrorMessage } from '@/services'

export type BackendStatus = 'checking' | 'online' | 'offline'

export interface BackendHealth {
  status: BackendStatus
  /** Round-trip time of the last successful probe, in milliseconds. */
  latencyMs: number | null
  checkedAt: Date | null
  message: string | null
  recheck: () => void
}

const DEFAULT_POLL_INTERVAL_MS = 30_000

/**
 * Polls the backend root endpoint so the header can report real service
 * reachability instead of a decorative indicator. Polling pauses while the
 * document is hidden and resumes on focus.
 */
export function useBackendStatus(
  pollIntervalMs: number = DEFAULT_POLL_INTERVAL_MS,
): BackendHealth {
  const [health, setHealth] = useState<Omit<BackendHealth, 'recheck'>>({
    status: 'checking',
    latencyMs: null,
    checkedAt: null,
    message: null,
  })

  const mountedRef = useRef(true)
  const controllerRef = useRef<AbortController | null>(null)

  const probe = useCallback(async () => {
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller

    const startedAt = performance.now()

    try {
      await fetchServiceInfo({ signal: controller.signal })
      if (!mountedRef.current) return

      setHealth({
        status: 'online',
        latencyMs: Math.round(performance.now() - startedAt),
        checkedAt: new Date(),
        message: null,
      })
    } catch (error: unknown) {
      if (!mountedRef.current || isAbortError(error)) return

      setHealth({
        status: 'offline',
        latencyMs: null,
        checkedAt: new Date(),
        message: toErrorMessage(error),
      })
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true

    // Polling an external service is exactly what an effect is for; state is
    // only written once the async probe settles.
    // oxlint-disable-next-line react/set-state-in-effect
    void probe()

    const interval = window.setInterval(() => {
      if (document.visibilityState === 'visible') void probe()
    }, pollIntervalMs)

    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') void probe()
    }

    document.addEventListener('visibilitychange', onVisibilityChange)

    return () => {
      mountedRef.current = false
      window.clearInterval(interval)
      document.removeEventListener('visibilitychange', onVisibilityChange)
      controllerRef.current?.abort()
    }
  }, [probe, pollIntervalMs])

  const recheck = useCallback(() => {
    void probe()
  }, [probe])

  return { ...health, recheck }
}
