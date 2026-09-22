import type { CSSProperties, HTMLAttributes } from 'react'

import { useInViewOnce } from '@/hooks/useInViewOnce'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'
import { cn } from '@/lib/cn'

export interface RevealOnScrollProps extends HTMLAttributes<HTMLDivElement> {
  /** Stagger offset in ms — pass `index * 70` for a cascading group. */
  delayMs?: number
  /** Travel distance of the entrance slide, in pixels. */
  distance?: number
  /** Adds a very slight scale-in (0.97 → 1) alongside the fade/rise. */
  scale?: boolean
}

/**
 * Fades and lifts its children in once they cross into the viewport.
 * Each instance observes independently, so a grid of cards cascades in as
 * the user scrolls rather than firing all at once. A shared primitive —
 * intended for reuse when this visual language reaches the dashboard.
 */
export function RevealOnScroll({
  delayMs = 0,
  distance = 16,
  scale = false,
  className,
  style,
  children,
  ...rest
}: RevealOnScrollProps) {
  const { ref, inView } = useInViewOnce()
  const prefersReducedMotion = usePrefersReducedMotion()

  const revealed = prefersReducedMotion || inView

  const mergedStyle: CSSProperties = {
    ...style,
    transitionDelay: revealed && !prefersReducedMotion ? `${delayMs}ms` : undefined,
    transform: [
      `translateY(${revealed ? 0 : distance}px)`,
      scale ? `scale(${revealed ? 1 : 0.97})` : '',
    ]
      .filter(Boolean)
      .join(' '),
  }

  return (
    <div
      ref={ref}
      className={cn(
        'transition-[opacity,transform] duration-700 ease-out',
        revealed ? 'opacity-100' : 'opacity-0',
        className,
      )}
      style={mergedStyle}
      {...rest}
    >
      {children}
    </div>
  )
}
