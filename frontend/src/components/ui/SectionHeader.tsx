import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

export interface SectionHeaderProps {
  title: ReactNode
  eyebrow?: ReactNode
  description?: ReactNode
  actions?: ReactNode
  className?: string
}

/** Page- and section-level heading block with an optional action cluster. */
export function SectionHeader({
  title,
  eyebrow,
  description,
  actions,
  className,
}: SectionHeaderProps) {
  return (
    <div
      className={cn(
        'flex flex-wrap items-end justify-between gap-x-6 gap-y-3',
        className,
      )}
    >
      <div className="min-w-0">
        {eyebrow ? (
          <p className="mb-1.5 text-2xs font-semibold tracking-widest text-ink-faint uppercase">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="text-lg leading-tight font-semibold tracking-tight text-ink">
          {title}
        </h1>
        {description ? (
          <p className="mt-1.5 max-w-3xl text-xs leading-relaxed text-ink-muted">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex items-center gap-2">{actions}</div>
      ) : null}
    </div>
  )
}
