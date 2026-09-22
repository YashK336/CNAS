import { useEffect, useState } from 'react'

import { BrandMark } from '@/components/layout/BrandMark'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'
import { cn } from '@/lib/cn'

type Phase = 'enter' | 'exit' | 'done'

/**
 * Brief network-initialising moment shown once when the landing page first
 * mounts. Capped well under a second and skipped entirely under reduced
 * motion — it never blocks or delays interaction, only decorates it.
 */
export function EntryOverlay() {
  const prefersReducedMotion = usePrefersReducedMotion()
  const [phase, setPhase] = useState<Phase>(prefersReducedMotion ? 'done' : 'enter')

  useEffect(() => {
    if (prefersReducedMotion) return

    const exitTimer = window.setTimeout(() => setPhase('exit'), 420)
    const doneTimer = window.setTimeout(() => setPhase('done'), 680)

    return () => {
      window.clearTimeout(exitTimer)
      window.clearTimeout(doneTimer)
    }
  }, [prefersReducedMotion])

  if (phase === 'done') return null

  return (
    <div
      aria-hidden
      className={cn(
        'fixed inset-0 z-[100] flex items-center justify-center bg-canvas transition-opacity duration-300 ease-out',
        phase === 'exit' ? 'opacity-0' : 'opacity-100',
      )}
    >
      <div className="relative flex h-20 w-20 items-center justify-center">
        <span className="absolute inset-0 rounded-full border border-accent/35 motion-safe:animate-[cnas-ring-expand_0.68s_ease-out_forwards]" />
        <span className="absolute inset-0 rounded-full border border-accent/20 motion-safe:animate-[cnas-ring-expand_0.68s_ease-out_0.1s_forwards]" />
        <BrandMark
          size={34}
          className="relative motion-safe:animate-[cnas-rise_0.36s_ease-out_both]"
        />
      </div>
    </div>
  )
}
