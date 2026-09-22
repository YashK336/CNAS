import { useEffect, useRef, useState } from 'react'

/**
 * Reports whether an element has entered the viewport, once. Used to drive
 * scroll-reveal entrance transitions without re-triggering on scroll-back —
 * the landing page's primary motion primitive, reusable for the
 * authenticated dashboard later.
 */
export function useInViewOnce(threshold = 0.15) {
  const ref = useRef<HTMLDivElement | null>(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    if (inView) return
    const el = ref.current
    if (!el) return

    if (typeof IntersectionObserver === 'undefined') {
      setInView(true)
      return
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setInView(true)
        }
      },
      { threshold, rootMargin: '0px 0px -60px 0px' },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [inView, threshold])

  return { ref, inView } as const
}
