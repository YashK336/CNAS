import type { ComponentPropsWithoutRef } from 'react'

import { cn } from '@/lib/cn'
import { useBackdropZone } from './useBackdropZone'

export interface LandingSectionProps extends ComponentPropsWithoutRef<'section'> {
  /** 0 (backdrop barely visible) – 1 (backdrop at full energy). */
  intensity: number
  /** Tailwind background-opacity utility tinting content over the shared backdrop. */
  tint?: string
}

/**
 * Standard landing-page section shell: registers a backdrop intensity zone
 * and applies a translucent tint over the shared `LandingBackdrop` so the
 * network stays visible-but-restrained behind readable content. This is
 * what keeps the page reading as one continuous environment instead of a
 * dark background that goes flat after the hero.
 */
export function LandingSection({
  intensity,
  tint = 'bg-canvas/55',
  className,
  children,
  ...rest
}: LandingSectionProps) {
  const ref = useBackdropZone<HTMLElement>(intensity)

  return (
    <section ref={ref} className={cn('relative', tint, className)} {...rest}>
      {children}
    </section>
  )
}
