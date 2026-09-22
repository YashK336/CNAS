import { ChevronDown } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

export interface DisclosureProps {
  /** Always-visible summary row. */
  title: ReactNode
  /** Optional short line shown next to the title, e.g. a plain-language gloss. */
  subtitle?: ReactNode
  /** Revealed technical detail. */
  children: ReactNode
  className?: string
  defaultOpen?: boolean
}

/**
 * Native `<details>`-backed expandable row: no JS state, keyboard and
 * screen-reader support come for free, and it degrades gracefully. Styled
 * to match the CNAS panel language. Generic enough to reuse for
 * "show technical detail" affordances in the authenticated dashboard.
 */
export function Disclosure({
  title,
  subtitle,
  children,
  className,
  defaultOpen = false,
}: DisclosureProps) {
  return (
    <details
      className={cn(
        'group rounded-md border border-line bg-surface open:bg-surface-raised transition-colors duration-300',
        className,
      )}
      open={defaultOpen}
    >
      <summary className="flex cursor-pointer list-none items-start justify-between gap-3 px-4 py-3.5 [&::-webkit-details-marker]:hidden">
        <div>
          <p className="text-sm font-semibold text-ink">{title}</p>
          {subtitle ? (
            <p className="mt-1 text-xs leading-relaxed text-ink-muted">{subtitle}</p>
          ) : null}
        </div>
        <ChevronDown
          size={16}
          strokeWidth={1.75}
          className="mt-0.5 shrink-0 text-ink-faint transition-transform duration-300 group-open:rotate-180 group-open:text-accent"
        />
      </summary>
      <div className="border-t border-line/70 px-4 py-3.5 text-xs leading-relaxed text-ink-muted">
        {children}
      </div>
    </details>
  )
}
