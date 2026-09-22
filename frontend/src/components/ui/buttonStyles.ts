import { cn } from '@/lib/cn'
import type { ClassValue } from '@/lib/cn'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
export type ButtonSize = 'sm' | 'md'

const BASE_CLASS =
  'inline-flex select-none items-center justify-center gap-1.5 rounded-sm border whitespace-nowrap font-medium transition-colors disabled:pointer-events-none disabled:opacity-45'

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary:
    'border-accent/55 bg-accent/15 text-accent hover:border-accent/80 hover:bg-accent/25',
  secondary:
    'border-line-strong bg-surface-raised text-ink hover:bg-surface-hover',
  ghost:
    'border-transparent text-ink-muted hover:bg-surface-hover hover:text-ink',
  danger:
    'border-signal-critical/45 bg-signal-critical/12 text-signal-critical hover:bg-signal-critical/20',
}

const SIZE_CLASS: Record<ButtonSize, string> = {
  sm: 'h-7 px-2.5 text-2xs',
  md: 'h-8 px-3 text-xs',
}

/** Shared between `Button` and `LinkButton` so the two never drift. */
export function buttonClass(
  variant: ButtonVariant = 'secondary',
  size: ButtonSize = 'md',
  className?: ClassValue,
): string {
  return cn(BASE_CLASS, VARIANT_CLASS[variant], SIZE_CLASS[size], className)
}
