import { AnomalyBadge } from '@/components/anomaly/AnomalyBadge'
import {
  Panel,
  PanelBody,
  PanelHeader,
  SectionError,
  Skeleton,
} from '@/components/ui'
import { ANOMALY_LEVEL_PRESENTATION } from '@/lib/anomaly'
import { formatNumber } from '@/lib/format'
import { ANOMALY_LEVELS } from '@/types'
import type { AnomalyDistribution } from '@/types'

export interface AnomalyDistributionPanelProps {
  total: number | null
  distribution: AnomalyDistribution | null
  isLoading: boolean
  error: string | null
  onRetry: () => void
}

export function AnomalyDistributionPanel({
  total,
  distribution,
  isLoading,
  error,
  onRetry,
}: AnomalyDistributionPanelProps) {
  const buckets = distribution
    ? [...ANOMALY_LEVELS].reverse().map((level) => {
        const count = distribution[level]
        const percentage = total && total > 0 ? (count / total) * 100 : 0
        return { level, count, percentage }
      })
    : null

  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title="Anomaly distribution"
        description="People per behavioral-anomaly band from GET /analytics/anomalies."
      />

      {error && !buckets ? (
        <SectionError message={error} onRetry={onRetry} compact />
      ) : (
        <PanelBody className="flex flex-1 flex-col gap-2.5">
          {buckets
            ? buckets.map((bucket) => (
                <div key={bucket.level} className="flex items-center gap-3">
                  <span className="w-[78px] shrink-0">
                    <AnomalyBadge level={bucket.level} />
                  </span>
                  <span className="h-1 min-w-0 flex-1 overflow-hidden rounded-sm bg-surface-active">
                    <span
                      className={`block h-full rounded-sm ${ANOMALY_LEVEL_PRESENTATION[bucket.level].barClass}`}
                      style={{ width: `${bucket.percentage}%` }}
                    />
                  </span>
                  <span className="w-8 shrink-0 text-right font-mono text-xs text-ink tabular-nums">
                    {formatNumber(bucket.count)}
                  </span>
                  <span className="w-12 shrink-0 text-right font-mono text-2xs text-ink-muted tabular-nums">
                    {bucket.percentage.toFixed(1)}%
                  </span>
                </div>
              ))
            : ANOMALY_LEVELS.map((level) => (
                <div key={level} className="flex items-center gap-3">
                  <Skeleton className="h-4 w-[78px] shrink-0" />
                  <Skeleton className="h-1 min-w-0 flex-1" />
                  <Skeleton className="h-3 w-8 shrink-0" />
                  <Skeleton className="h-3 w-12 shrink-0" />
                </div>
              ))}

          <p className="mt-auto border-t border-line pt-2.5 text-2xs text-ink-faint">
            {total !== null ? (
              <>
                <span className="font-mono text-ink-muted tabular-nums">
                  {formatNumber(total)}
                </span>{' '}
                people scored · unusual activity vs the current dataset, not a
                finding of criminal behavior
              </>
            ) : (
              <Skeleton className="h-3 w-40" />
            )}
          </p>

          {isLoading ? (
            <span className="sr-only">Loading anomaly distribution</span>
          ) : null}
        </PanelBody>
      )}
    </Panel>
  )
}
