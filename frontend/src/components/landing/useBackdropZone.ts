import { useEffect, useRef } from 'react'

import { setBackdropIntensity } from './backdropIntensity'

/**
 * Registers an element as a "zone" that sets the shared page backdrop's
 * target intensity whenever it crosses the middle of the viewport. Attach
 * the returned ref to a section's root element.
 */
export function useBackdropZone<T extends HTMLElement = HTMLElement>(intensity: number) {
  const ref = useRef<T | null>(null)

  useEffect(() => {
    const el = ref.current
    if (!el || typeof IntersectionObserver === 'undefined') return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setBackdropIntensity(intensity)
        }
      },
      { threshold: 0.45 },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [intensity])

  return ref
}
