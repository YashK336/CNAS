import type { HTMLAttributes, ReactNode } from 'react'

import { cn } from '@/lib/cn'

export interface PanelProps extends HTMLAttributes<HTMLDivElement> {
  /** Slightly lighter fill, for panels sitting on top of another panel. */
  raised?: boolean
}

export function Panel({
  raised = false,
  className,
  children,
  ...rest
}: PanelProps) {
  return (
    <div
      className={cn(
        'rounded-md border border-line',
        raised ? 'bg-surface-raised' : 'bg-surface',
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  )
}

export interface PanelHeaderProps {
  title: ReactNode
  /** Small uppercase label above the title. */
  eyebrow?: ReactNode
  description?: ReactNode
  actions?: ReactNode
  icon?: ReactNode
  className?: string
}

export function PanelHeader({
  title,
  eyebrow,
  description,
  actions,
  icon,
  className,
}: PanelHeaderProps) {
  return (
    <div
      className={cn(
        'flex items-start justify-between gap-4 border-b border-line px-4 py-3',
        className,
      )}
    >
      <div className="flex min-w-0 items-start gap-2.5">
        {icon ? <span className="mt-0.5 text-ink-faint">{icon}</span> : null}
        <div className="min-w-0">
          {eyebrow ? (
            <p className="mb-1 text-2xs font-semibold tracking-widest text-ink-faint uppercase">
              {eyebrow}
            </p>
          ) : null}
          <h2 className="truncate text-sm font-semibold text-ink">{title}</h2>
          {description ? (
            <p className="mt-1 text-xs leading-relaxed text-ink-muted">
              {description}
            </p>
          ) : null}
        </div>
      </div>
      {actions ? (
        <div className="flex shrink-0 items-center gap-2">{actions}</div>
      ) : null}
    </div>
  )
}

export function PanelBody({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('p-4', className)} {...rest}>
      {children}
    </div>
  )
}
