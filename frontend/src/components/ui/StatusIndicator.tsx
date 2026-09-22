import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

export type StatusTone = 'online' | 'degraded' | 'offline' | 'pending'

const DOT_CLASS: Record<StatusTone, string> = {
  online: 'bg-signal-low',
  degraded: 'bg-signal-medium',
  offline: 'bg-signal-critical',
  pending: 'bg-ink-faint',
}

const LABEL_CLASS: Record<StatusTone, string> = {
  online: 'text-signal-low',
  degraded: 'text-signal-medium',
  offline: 'text-signal-critical',
  pending: 'text-ink-faint',
}

export interface StatusIndicatorProps {
  tone: StatusTone
  label: ReactNode
  /** Secondary detail, e.g. latency or last-checked time. */
  detail?: ReactNode
  className?: string
  title?: string
}

export function StatusIndicator({
  tone,
  label,
  detail,
  className,
  title,
}: StatusIndicatorProps) {
  return (
    <span
      className={cn('inline-flex items-center gap-2', className)}
      title={title}
    >
      <span className="relative flex h-1.5 w-1.5 shrink-0">
        {tone === 'pending' ? (
          <span
            className={cn(
              'absolute inline-flex h-full w-full animate-ping rounded-full opacity-60',
              DOT_CLASS[tone],
            )}
          />
        ) : null}
        <span
          className={cn(
            'relative inline-flex h-1.5 w-1.5 rounded-full',
            DOT_CLASS[tone],
          )}
        />
      </span>
      <span
        className={cn(
          'text-2xs font-medium tracking-wide uppercase',
          LABEL_CLASS[tone],
        )}
      >
        {label}
      </span>
      {detail ? (
        <span className="font-mono text-2xs text-ink-faint tabular-nums">
          {detail}
        </span>
      ) : null}
    </span>
  )
}
