import { MapPin, ScrollText, Shield, Users } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import { Panel, Skeleton } from '@/components/ui'
import { formatNumber } from '@/lib/format'
import type { CaseSummary } from '@/types'

export interface CasesSummaryStripProps {
  summary: CaseSummary | null
  isLoading: boolean
}

interface MetricDefinition {
  label: string
  icon: LucideIcon
  read: (summary: CaseSummary) => number
}

const METRICS: MetricDefinition[] = [
  { label: 'Total FIRs', icon: ScrollText, read: (s) => s.total },
  { label: 'Crime types', icon: Shield, read: (s) => s.crimes },
  { label: 'Locations', icon: MapPin, read: (s) => s.locations },
  { label: 'People involved', icon: Users, read: (s) => s.people },
]

export function CasesSummaryStrip({
  summary,
  isLoading,
}: CasesSummaryStripProps) {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {METRICS.map((metric) => {
        const Icon = metric.icon

        return (
          <Panel key={metric.label} className="px-3 py-2.5">
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-2xs font-semibold tracking-wider text-ink-faint uppercase">
                {metric.label}
              </span>
              <Icon
                size={13}
                strokeWidth={1.75}
                className="shrink-0 text-ink-faint"
                aria-hidden
              />
            </div>

            {summary ? (
              <p className="mt-1.5 font-mono text-lg leading-none text-ink tabular-nums">
                {formatNumber(metric.read(summary))}
              </p>
            ) : (
              <Skeleton className="mt-1.5 h-[18px] w-16" />
            )}
          </Panel>
        )
      })}

      {isLoading ? <span className="sr-only">Loading FIR totals</span> : null}
    </div>
  )
}
