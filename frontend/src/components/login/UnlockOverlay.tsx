import { useEffect, useRef, useState } from 'react'

import { BrandMark } from '@/components/layout/BrandMark'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'
import { cn } from '@/lib/cn'

const DURATION_MS = 560

type Phase = 'verify' | 'enter'

export interface UnlockOverlayProps {
  /** Fires once the short visual has played (or immediately under reduced motion). */
  onComplete: () => void
}

/**
 * Graph-inspired unlock shown after authentication succeeds and before the
 * dashboard route is committed. Capped under 0.7s and skipped entirely
 * when the user prefers reduced motion — it never re-runs the login request.
 */
export function UnlockOverlay({ onComplete }: UnlockOverlayProps) {
  const prefersReducedMotion = usePrefersReducedMotion()
  const [phase, setPhase] = useState<Phase>('verify')
  const completedRef = useRef(false)
  const onCompleteRef = useRef(onComplete)

  useEffect(() => {
    onCompleteRef.current = onComplete
  }, [onComplete])

  useEffect(() => {
    const finish = () => {
      if (completedRef.current) return
      completedRef.current = true
      onCompleteRef.current()
    }

    if (prefersReducedMotion) {
      finish()
      return
    }

    const enterTimer = window.setTimeout(() => setPhase('enter'), 220)
    const doneTimer = window.setTimeout(finish, DURATION_MS)

    return () => {
      window.clearTimeout(enterTimer)
      window.clearTimeout(doneTimer)
    }
  }, [prefersReducedMotion])

  if (prefersReducedMotion) return null

  return (
    <div
      aria-live="polite"
      className="fixed inset-0 z-[110] flex items-center justify-center bg-canvas/80 backdrop-blur-[2px]"
    >
      <div className="relative flex flex-col items-center gap-4">
        <div className="relative flex h-24 w-24 items-center justify-center">
          <span className="absolute inset-0 rounded-full border border-accent/40 motion-safe:animate-[cnas-ring-expand_0.56s_ease-out_forwards]" />
          <span className="absolute inset-2 rounded-full border border-accent/20 motion-safe:animate-[cnas-ring-expand_0.56s_ease-out_0.08s_forwards]" />
          <span
            aria-hidden
            className="absolute h-px w-16 origin-center bg-accent/50 motion-safe:animate-[cnas-unlock-line_0.56s_ease-out_forwards]"
          />
          <BrandMark size={36} className="relative" />
        </div>
        <p
          className={cn(
            'font-mono text-2xs tracking-[0.18em] text-accent uppercase',
            'motion-safe:animate-[cnas-rise_0.28s_ease-out_both]',
          )}
        >
          {phase === 'verify' ? 'Verifying access' : 'Entering CNAS'}
        </p>
      </div>
    </div>
  )
}
