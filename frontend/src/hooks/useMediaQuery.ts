import { useCallback, useSyncExternalStore } from 'react'

/**
 * Tracks a CSS media query. Used to force the sidebar into its icon rail on
 * tablet widths, where a full-width nav would eat the analysis canvas.
 */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onStoreChange: () => void) => {
      const mediaQueryList = window.matchMedia(query)
      mediaQueryList.addEventListener('change', onStoreChange)
      return () => mediaQueryList.removeEventListener('change', onStoreChange)
    },
    [query],
  )

  const getSnapshot = useCallback(
    () => window.matchMedia(query).matches,
    [query],
  )

  return useSyncExternalStore(subscribe, getSnapshot)
}
