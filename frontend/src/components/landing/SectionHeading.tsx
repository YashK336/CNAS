import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

export interface SectionHeadingProps {
  eyebrow?: ReactNode
  title: ReactNode
  description?: ReactNode
  align?: 'left' | 'center'
  className?: string
}

/**
 * Marketing-scale section heading. Distinct from the dashboard's
 * `SectionHeader` (which is sized for dense workstation panels) — this one
 * carries the display type used throughout the public landing page.
 */
export function SectionHeading({
  eyebrow,
  title,
  description,
  align = 'left',
  className,
}: SectionHeadingProps) {
  return (
    <div
      className={cn(
        'max-w-2xl',
        align === 'center' && 'mx-auto text-center',
        className,
      )}
    >
      {eyebrow ? (
        <div
          className={cn(
            'mb-3 flex items-center gap-2 text-2xs font-semibold tracking-[0.2em] text-accent uppercase',
            align === 'center' && 'justify-center',
          )}
        >
          <span aria-hidden className="h-px w-4 bg-accent/50" />
          {eyebrow}
        </div>
      ) : null}
      <h2 className="text-2xl leading-tight font-semibold tracking-tight text-ink sm:text-3xl">
        {title}
      </h2>
      {description ? (
        <p className="mt-3 text-sm leading-relaxed text-ink-muted sm:text-base">
          {description}
        </p>
      ) : null}
    </div>
  )
}
