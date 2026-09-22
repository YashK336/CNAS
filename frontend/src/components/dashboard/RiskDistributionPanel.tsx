import { RiskBadge } from '@/components/risk'
import {
  Panel,
  PanelBody,
  PanelHeader,
  SectionError,
  Skeleton,
} from '@/components/ui'
import { buildRiskDistribution, readScoringMethod } from '@/lib/dashboard'
import { RISK_LEVEL_PRESENTATION } from '@/lib/risk'
import { formatNumber } from '@/lib/format'
import { RISK_LEVELS } from '@/types'
import type { RiskProfile } from '@/types'

export interface RiskDistributionPanelProps {
  profiles: RiskProfile[] | null
  isLoading: boolean
  error: string | null
  onRetry: () => void
}

export function RiskDistributionPanel({
  profiles,
  isLoading,
  error,
  onRetry,
}: RiskDistributionPanelProps) {
  const distribution = profiles ? buildRiskDistribution(profiles) : null
  const scoringMethod = readScoringMethod(profiles)

  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title="Risk distribution"
        description="People per risk band, counted from GET /analytics/risk."
      />

      {error && !distribution ? (
        <SectionError message={error} onRetry={onRetry} compact />
      ) : (
        <PanelBody className="flex flex-1 flex-col gap-2.5">
          {distribution
            ? distribution.buckets.map((bucket) => (
                <div key={bucket.level} className="flex items-center gap-3">
                  <span className="w-[68px] shrink-0">
                    <RiskBadge level={bucket.level} />
                  </span>

                  <span className="h-1 min-w-0 flex-1 overflow-hidden rounded-sm bg-surface-active">
                    <span
                      className={`block h-full rounded-sm ${RISK_LEVEL_PRESENTATION[bucket.level].barClass}`}
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
            : RISK_LEVELS.map((level) => (
                <div key={level} className="flex items-center gap-3">
                  <Skeleton className="h-4 w-[68px] shrink-0" />
                  <Skeleton className="h-1 min-w-0 flex-1" />
                  <Skeleton className="h-3 w-8 shrink-0" />
                  <Skeleton className="h-3 w-12 shrink-0" />
                </div>
              ))}

          <div className="mt-auto flex items-center justify-between gap-3 border-t border-line pt-2.5 text-2xs text-ink-faint">
            {distribution ? (
              <span>
                <span className="font-mono text-ink-muted tabular-nums">
                  {formatNumber(distribution.total)}
                </span>{' '}
                people scored
              </span>
            ) : (
              <Skeleton className="h-3 w-28" />
            )}

            {scoringMethod ? (
              <span className="font-mono">{scoringMethod}</span>
            ) : null}
          </div>

          {isLoading ? (
            <span className="sr-only">Loading risk distribution</span>
          ) : null}
        </PanelBody>
      )}
    </Panel>
  )
}
