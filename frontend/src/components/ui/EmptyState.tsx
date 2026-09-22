import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

export interface EmptyStateProps {
  title: ReactNode
  description?: ReactNode
  icon?: ReactNode
  actions?: ReactNode
  className?: string
}

/** Neutral state used for "nothing here yet", empty results and errors. */
export function EmptyState({
  title,
  description,
  icon,
  actions,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center px-6 py-12 text-center',
        className,
      )}
    >
      {icon ? (
        <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-md border border-line bg-surface-raised text-ink-faint">
          {icon}
        </div>
      ) : null}
      <p className="text-sm font-medium text-ink">{title}</p>
      {description ? (
        <p className="mt-1.5 max-w-md text-xs leading-relaxed text-ink-muted">
          {description}
        </p>
      ) : null}
      {actions ? (
        <div className="mt-4 flex items-center gap-2">{actions}</div>
      ) : null}
    </div>
  )
}
