import { RefreshCw } from 'lucide-react'

import {
  AnomalyDistributionPanel,
  AnomalySubjectsPanel,
} from '@/components/anomaly'
import {
  An2FindingsPanel,
  AnalyticsOverviewStrip,
  CentralityRankingPanel,
  HighestRiskPanel,
} from '@/components/analytics'
import { CommunityOverviewPanel, RiskDistributionPanel } from '@/components/dashboard'
import { Button, SectionHeader } from '@/components/ui'
import { useAnalyticsData } from '@/hooks'
import { cn } from '@/lib/cn'
import { formatTime } from '@/lib/format'

export function AnalyticsPage() {
  const {
    statistics,
    centrality,
    communities,
    risk,
    anomalies,
    topByPageRank,
    topByBetweenness,
    highestRisk,
    isLoading,
    lastRefreshedAt,
    refreshAll,
  } = useAnalyticsData()

  return (
    <div className="space-y-4">
      <SectionHeader
        eyebrow="Graph analytics"
        title="Analytics"
        description="Centrality rankings, community structure, risk distribution and behavioral anomaly indicators over the constructed network."
        actions={
          <div className="flex items-center gap-4">
            {lastRefreshedAt ? (
              <span className="hidden text-2xs text-ink-faint sm:block">
                Last loaded{' '}
                <span className="font-mono text-ink-muted">
                  {formatTime(lastRefreshedAt)}
                </span>
              </span>
            ) : null}

            <Button
              size="sm"
              onClick={refreshAll}
              disabled={isLoading}
              icon={
                <RefreshCw
                  size={13}
                  strokeWidth={1.75}
                  className={cn(isLoading && 'animate-spin')}
                />
              }
            >
              {isLoading ? 'Loading' : 'Refresh'}
            </Button>
          </div>
        }
      />

      <section className="space-y-2">
        <p className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">
          Overview
        </p>
        <AnalyticsOverviewStrip
          statistics={statistics.data}
          isLoading={statistics.isLoading}
          error={statistics.error}
          onRetry={statistics.refetch}
        />
      </section>

      <section className="space-y-2">
        <p className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">
          Investigator findings
        </p>
        <An2FindingsPanel />
      </section>

      <section className="space-y-2">
        <p className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">
          Network intelligence
        </p>
        <div className="grid gap-4 xl:grid-cols-2">
          <CentralityRankingPanel
            title="Top people by PageRank"
            description="Influence ranking from GET /analytics/centrality."
            rankKey="pagerank"
            results={topByPageRank}
            isLoading={centrality.isLoading}
            error={centrality.error}
            onRetry={centrality.refetch}
          />

          <CentralityRankingPanel
            title="Top people by betweenness"
            description="Bridge-role ranking from GET /analytics/centrality."
            rankKey="betweenness_centrality"
            results={topByBetweenness}
            isLoading={centrality.isLoading}
            error={centrality.error}
            onRetry={centrality.refetch}
          />
        </div>
      </section>

      <section className="space-y-2">
        <p className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">
          Communities
        </p>
        <CommunityOverviewPanel
          communities={communities.data}
          isLoading={communities.isLoading}
          error={communities.error}
          onRetry={communities.refetch}
        />
      </section>

      <section className="space-y-2">
        <p className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">
          Risk analytics
        </p>
        <div className="grid gap-4 xl:grid-cols-[minmax(0,320px)_minmax(0,1fr)]">
          <RiskDistributionPanel
            profiles={risk.data}
            isLoading={risk.isLoading}
            error={risk.error}
            onRetry={risk.refetch}
          />

          <HighestRiskPanel
            profiles={highestRisk}
            isLoading={risk.isLoading}
            error={risk.error}
            onRetry={risk.refetch}
          />
        </div>
      </section>

      <section className="space-y-2">
        <p className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">
          Behavioral anomalies
        </p>
        <div className="grid gap-4 xl:grid-cols-[minmax(0,320px)_minmax(0,1fr)]">
          <AnomalyDistributionPanel
            total={anomalies.data?.total ?? null}
            distribution={anomalies.data?.distribution ?? null}
            isLoading={anomalies.isLoading}
            error={anomalies.error}
            onRetry={anomalies.refetch}
          />

          <AnomalySubjectsPanel
            profiles={anomalies.data?.data ?? null}
            isLoading={anomalies.isLoading}
            error={anomalies.error}
            onRetry={anomalies.refetch}
          />
        </div>
      </section>
    </div>
  )
}
