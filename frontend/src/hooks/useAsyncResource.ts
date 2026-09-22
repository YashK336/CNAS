import { useCallback, useEffect, useRef, useState } from 'react'

import { isAbortError, toErrorMessage } from '@/services'
import type { RequestOptions } from '@/services'

export type AsyncStatus = 'loading' | 'success' | 'error'

export interface AsyncResource<T> {
  data: T | null
  error: string | null
  status: AsyncStatus
  isLoading: boolean
  /** When the last attempt settled, for staleness reporting. */
  settledAt: Date | null
  refetch: () => void
}

interface AsyncState<T> {
  data: T | null
  error: string | null
  status: AsyncStatus
  settledAt: Date | null
}

/**
 * Fetches a cancellable resource and tracks loading/error state.
 *
 * `fetcher` is read through a ref, so inline arrow functions are safe: the
 * request re-runs only when `deps` change or `refetch()` is called. Previous
 * data is kept while refetching to avoid layout shift.
 */
export function useAsyncResource<T>(
  fetcher: (options: RequestOptions) => Promise<T>,
  deps: readonly unknown[] = [],
): AsyncResource<T> {
  const fetcherRef = useRef(fetcher)
  const [reloadToken, setReloadToken] = useState(0)
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    error: null,
    status: 'loading',
    settledAt: null,
  })

  useEffect(() => {
    fetcherRef.current = fetcher
  })

  useEffect(() => {
    const controller = new AbortController()
    let active = true

    // Intentional: a refetch must show the loading state again while keeping
    // the previous data on screen.
    // oxlint-disable-next-line react/set-state-in-effect
    setState((previous) => ({
      data: previous.data,
      error: null,
      status: 'loading',
      settledAt: previous.settledAt,
    }))

    fetcherRef
      .current({ signal: controller.signal })
      .then((data) => {
        if (!active) return
        setState({
          data,
          error: null,
          status: 'success',
          settledAt: new Date(),
        })
      })
      .catch((error: unknown) => {
        if (!active || isAbortError(error)) return
        setState({
          data: null,
          error: toErrorMessage(error),
          status: 'error',
          settledAt: new Date(),
        })
      })

    return () => {
      active = false
      controller.abort()
    }
    // Caller-provided deps are spread intentionally; `fetcher` is held in a ref.
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, reloadToken])

  const refetch = useCallback(() => {
    setReloadToken((token) => token + 1)
  }, [])

  return {
    data: state.data,
    error: state.error,
    status: state.status,
    isLoading: state.status === 'loading',
    settledAt: state.settledAt,
    refetch,
  }
}
