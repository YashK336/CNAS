import { Car, Cctv, ScrollText, Users, Waypoints } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import { Panel, SectionError, Skeleton } from '@/components/ui'
import { formatNumber } from '@/lib/format'
import type { NetworkStatistics } from '@/types'

export interface MetricsStripProps {
  statistics: NetworkStatistics | null
  isLoading: boolean
  error: string | null
  onRetry: () => void
}

interface MetricDefinition {
  label: string
  icon: LucideIcon
  read: (statistics: NetworkStatistics) => number
}

const METRICS: MetricDefinition[] = [
  { label: 'People', icon: Users, read: (s) => s.people },
  { label: 'Network links', icon: Waypoints, read: (s) => s.edges },
  { label: 'Vehicles', icon: Car, read: (s) => s.vehicles },
  { label: 'Crime events', icon: ScrollText, read: (s) => s.crime_events },
  {
    label: 'Surveillance events',
    icon: Cctv,
    read: (s) => s.surveillance_events,
  },
]

export function MetricsStrip({
  statistics,
  isLoading,
  error,
  onRetry,
}: MetricsStripProps) {
  if (error && !statistics) {
    return (
      <Panel>
        <SectionError message={error} onRetry={onRetry} compact />
      </Panel>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
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

            {statistics ? (
              <p className="mt-1.5 font-mono text-lg leading-none text-ink tabular-nums">
                {formatNumber(metric.read(statistics))}
              </p>
            ) : (
              <Skeleton className="mt-1.5 h-[18px] w-16" />
            )}
          </Panel>
        )
      })}

      {isLoading ? <span className="sr-only">Loading network totals</span> : null}
    </div>
  )
}
