import type { ReactNode } from 'react'

import { Panel } from '@/components/ui'
import { cn } from '@/lib/cn'
import { formatNumber } from '@/lib/format'

export interface AssociationSectionProps {
  title: string
  icon: ReactNode
  /** Entities in this section; drives the count badge and the empty state. */
  count: number
  /** Shown when `count` is 0, describing the absence rather than implying it. */
  emptyMessage: string
  className?: string
  children: ReactNode
}

/** Uniform shell for one group of a person's associated entities. */
export function AssociationSection({
  title,
  icon,
  count,
  emptyMessage,
  className,
  children,
}: AssociationSectionProps) {
  return (
    <Panel raised className={cn('flex min-w-0 flex-col', className)}>
      <div className="flex items-center gap-2 border-b border-line px-3 py-2">
        <span aria-hidden className="text-ink-faint">
          {icon}
        </span>
        <h3 className="flex-1 truncate text-2xs font-semibold tracking-widest text-ink uppercase">
          {title}
        </h3>
        <span className="shrink-0 font-mono text-2xs text-ink-faint tabular-nums">
          {formatNumber(count)}
        </span>
      </div>

      {count === 0 ? (
        <p className="px-3 py-2.5 text-2xs text-ink-faint">{emptyMessage}</p>
      ) : (
        // Scrolls rather than truncates, so no derived record is ever hidden.
        <ul className="max-h-60 divide-y divide-line overflow-y-auto">
          {children}
        </ul>
      )}
    </Panel>
  )
}
