import {
  Panel,
  PanelBody,
  PanelHeader,
  SectionError,
  Skeleton,
} from '@/components/ui'
import { buildNetworkComposition } from '@/lib/dashboard'
import { formatNumber } from '@/lib/format'
import type { NetworkStatistics, NetworkSummary } from '@/types'

export interface NetworkSnapshotPanelProps {
  summary: NetworkSummary | null
  summaryError: string | null
  statistics: NetworkStatistics | null
  statisticsError: string | null
  isLoading: boolean
  onRetry: () => void
}

/**
 * Lightweight network overview. The full link chart lives in Network Explorer —
 * rendering thousands of edges here would cost a second graph rebuild.
 */
export function NetworkSnapshotPanel({
  summary,
  summaryError,
  statistics,
  statisticsError,
  isLoading,
  onRetry,
}: NetworkSnapshotPanelProps) {
  const composition = statistics ? buildNetworkComposition(statistics) : null
  const bothFailed = Boolean(summaryError && statisticsError)

  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title="Network snapshot"
        description="Size and node composition of the constructed graph."
      />

      {bothFailed ? (
        <SectionError
          message={summaryError ?? 'Network data unavailable'}
          onRetry={onRetry}
          compact
        />
      ) : (
        <PanelBody className="flex flex-1 flex-col gap-4">
          <div className="grid grid-cols-2 gap-3">
            {(
              [
                { label: 'Nodes', value: summary?.nodes },
                { label: 'Links', value: summary?.edges },
              ] as const
            ).map((item) => (
              <div
                key={item.label}
                className="rounded-sm border border-line bg-surface-raised px-3 py-2"
              >
                <p className="text-2xs font-semibold tracking-wider text-ink-faint uppercase">
                  {item.label}
                </p>
                {item.value === undefined ? (
                  summaryError ? (
                    <p className="mt-1.5 font-mono text-lg leading-none text-ink-faint">
                      —
                    </p>
                  ) : (
                    <Skeleton className="mt-1.5 h-[18px] w-14" />
                  )
                ) : (
                  <p className="mt-1.5 font-mono text-lg leading-none text-ink tabular-nums">
                    {formatNumber(item.value)}
                  </p>
                )}
              </div>
            ))}
          </div>

          <div className="flex flex-1 flex-col gap-2">
            <p className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">
              Node composition
            </p>

            {statisticsError && !composition ? (
              <p className="text-2xs text-signal-medium">
                Composition unavailable — /analytics/statistics did not respond.
              </p>
            ) : composition ? (
              composition.map((slice) => (
                <div key={slice.label} className="flex items-center gap-3">
                  <span className="w-24 shrink-0 truncate text-xs text-ink-muted">
                    {slice.label}
                  </span>
                  <span className="h-1 min-w-0 flex-1 overflow-hidden rounded-sm bg-surface-active">
                    <span
                      className="block h-full rounded-sm bg-accent/70"
                      style={{ width: `${slice.percentage}%` }}
                    />
                  </span>
                  <span className="w-8 shrink-0 text-right font-mono text-xs text-ink tabular-nums">
                    {formatNumber(slice.count)}
                  </span>
                  <span className="w-12 shrink-0 text-right font-mono text-2xs text-ink-muted tabular-nums">
                    {slice.percentage.toFixed(1)}%
                  </span>
                </div>
              ))
            ) : (
              Array.from({ length: 4 }, (_, index) => (
                <div key={index} className="flex items-center gap-3">
                  <Skeleton className="h-3 w-24 shrink-0" />
                  <Skeleton className="h-1 min-w-0 flex-1" />
                  <Skeleton className="h-3 w-8 shrink-0" />
                  <Skeleton className="h-3 w-12 shrink-0" />
                </div>
              ))
            )}
          </div>

          {isLoading ? (
            <span className="sr-only">Loading network snapshot</span>
          ) : null}
        </PanelBody>
      )}
    </Panel>
  )
}
