import { useCallback, useSyncExternalStore } from 'react'

const QUERY = '(prefers-reduced-motion: reduce)'

/**
 * Tracks the user's OS-level reduced-motion preference. Decorative
 * animation (canvas loops, drifting network backdrops) should read this
 * before starting a `requestAnimationFrame` loop; purely CSS-driven motion
 * is already neutralised globally in `index.css`.
 */
export function usePrefersReducedMotion(): boolean {
  const subscribe = useCallback((onStoreChange: () => void) => {
    const mediaQueryList = window.matchMedia(QUERY)
    mediaQueryList.addEventListener('change', onStoreChange)
    return () => mediaQueryList.removeEventListener('change', onStoreChange)
  }, [])

  const getSnapshot = useCallback(() => window.matchMedia(QUERY).matches, [])

  return useSyncExternalStore(subscribe, getSnapshot)
}
