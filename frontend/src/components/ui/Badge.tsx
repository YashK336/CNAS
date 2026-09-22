import type { HTMLAttributes } from 'react'

import { cn } from '@/lib/cn'

export type BadgeTone =
  | 'neutral'
  | 'accent'
  | 'low'
  | 'medium'
  | 'high'
  | 'critical'

const TONE_CLASS: Record<BadgeTone, string> = {
  neutral: 'border-line-strong bg-surface-raised text-ink-muted',
  accent: 'border-accent/35 bg-accent-muted text-accent',
  low: 'border-signal-low/35 bg-signal-low/10 text-signal-low',
  medium: 'border-signal-medium/35 bg-signal-medium/10 text-signal-medium',
  high: 'border-signal-high/40 bg-signal-high/10 text-signal-high',
  critical:
    'border-signal-critical/45 bg-signal-critical/12 text-signal-critical',
}

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone
  /** Tabular monospace, for IDs and codes. */
  mono?: boolean
}

export function Badge({
  tone = 'neutral',
  mono = false,
  className,
  children,
  ...rest
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 text-2xs leading-none',
        mono ? 'font-mono tracking-tight' : 'font-medium',
        TONE_CLASS[tone],
        className,
      )}
      {...rest}
    >
      {children}
    </span>
  )
}
