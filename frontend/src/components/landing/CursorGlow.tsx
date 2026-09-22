import { useEffect, useRef } from 'react'

import { useMediaQuery } from '@/hooks/useMediaQuery'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'

export type CursorGlowIntensity = 'default' | 'low'

const GLOW: Record<
  CursorGlowIntensity,
  { trailSize: string; leadSize: string; trail: string; lead: string }
> = {
  default: {
    trailSize: 'h-44 w-44',
    leadSize: 'h-52 w-52',
    trail: 'radial-gradient(circle, rgba(75,141,248,0.045) 0%, transparent 68%)',
    lead: 'radial-gradient(circle, rgba(96,153,249,0.07) 0%, transparent 70%)',
  },
  low: {
    trailSize: 'h-24 w-24',
    leadSize: 'h-28 w-28',
    trail: 'radial-gradient(circle, rgba(75,141,248,0.022) 0%, transparent 72%)',
    lead: 'radial-gradient(circle, rgba(96,153,249,0.035) 0%, transparent 74%)',
  },
}

/**
 * A very soft radial light that follows the pointer, plus a faintly lagging
 * echo layer that reads as a barely-there trail. Deliberately restrained —
 * closer to "the page is aware of the cursor" than a visible spotlight.
 * Skipped entirely on touch devices (no continuous pointer) and under
 * reduced motion. `low` is for quieter surfaces such as the login page.
 */
export function CursorGlow({ intensity = 'default' }: { intensity?: CursorGlowIntensity }) {
  const leadRef = useRef<HTMLDivElement>(null)
  const trailRef = useRef<HTMLDivElement>(null)
  const hasFinePointer = useMediaQuery('(pointer: fine)')
  const prefersReducedMotion = usePrefersReducedMotion()
  const enabled = hasFinePointer && !prefersReducedMotion

  useEffect(() => {
    if (!enabled) return

    const target = { x: window.innerWidth / 2, y: window.innerHeight / 2 }
    const trail = { ...target }
    let frameId = 0
    let hasMoved = false

    const handlePointerMove = (event: PointerEvent) => {
      target.x = event.clientX
      target.y = event.clientY
      hasMoved = true
    }

    const tick = () => {
      trail.x += (target.x - trail.x) * 0.08
      trail.y += (target.y - trail.y) * 0.08

      if (hasMoved && leadRef.current) {
        leadRef.current.style.transform = `translate3d(${target.x}px, ${target.y}px, 0)`
        leadRef.current.style.opacity = '1'
      }
      if (hasMoved && trailRef.current) {
        trailRef.current.style.transform = `translate3d(${trail.x}px, ${trail.y}px, 0)`
        trailRef.current.style.opacity = '1'
      }

      frameId = window.requestAnimationFrame(tick)
    }

    window.addEventListener('pointermove', handlePointerMove, { passive: true })
    frameId = window.requestAnimationFrame(tick)

    return () => {
      window.cancelAnimationFrame(frameId)
      window.removeEventListener('pointermove', handlePointerMove)
    }
  }, [enabled])

  if (!enabled) return null

  const glow = GLOW[intensity]

  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-40 overflow-hidden">
      {/* Trail: a faint, slightly-lagging echo — reads as motion, not a shape. */}
      <div
        ref={trailRef}
        className={`absolute top-0 left-0 ${glow.trailSize} -translate-x-1/2 -translate-y-1/2 rounded-full opacity-0 transition-opacity duration-500`}
        style={{
          background: glow.trail,
          mixBlendMode: 'screen',
        }}
      />
      <div
        ref={leadRef}
        className={`absolute top-0 left-0 ${glow.leadSize} -translate-x-1/2 -translate-y-1/2 rounded-full opacity-0 transition-opacity duration-500`}
        style={{
          background: glow.lead,
          mixBlendMode: 'screen',
        }}
      />
    </div>
  )
}
