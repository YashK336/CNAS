import { RefreshCw } from 'lucide-react'

import {
  CommunityOverviewPanel,
  DatasetStatusPanel,
  MetricsStrip,
  NetworkSnapshotPanel,
  RiskDistributionPanel,
  TopPrioritiesPanel,
} from '@/components/dashboard'
import { Button, SectionHeader } from '@/components/ui'
import { useDashboardData } from '@/hooks'
import { cn } from '@/lib/cn'
import { readScoringMethod } from '@/lib/dashboard'

export function DashboardPage() {
  const {
    statistics,
    risk,
    keyPersons,
    communities,
    networkSummary,
    anomalies,
    isLoading,
    apiReachability,
    networkAvailability,
    lastRefreshedAt,
    refreshAll,
  } = useDashboardData()

  const retryNetworkSnapshot = () => {
    networkSummary.refetch()
    statistics.refetch()
  }

  return (
    <div className="space-y-4">
      <SectionHeader
        eyebrow="Overview"
        title="Operations Dashboard"
        description="Current network intelligence and investigative priorities."
        actions={
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
        }
      />

      <MetricsStrip
        statistics={statistics.data}
        isLoading={statistics.isLoading}
        error={statistics.error}
        onRetry={statistics.refetch}
      />

      <div className="grid gap-4 xl:grid-cols-3">
        <RiskDistributionPanel
          profiles={risk.data}
          isLoading={risk.isLoading}
          error={risk.error}
          onRetry={risk.refetch}
        />

        <NetworkSnapshotPanel
          summary={networkSummary.data}
          summaryError={networkSummary.error}
          statistics={statistics.data}
          statisticsError={statistics.error}
          isLoading={networkSummary.isLoading || statistics.isLoading}
          onRetry={retryNetworkSnapshot}
        />

        <DatasetStatusPanel
          apiReachability={apiReachability}
          networkAvailability={networkAvailability}
          scoringMethod={readScoringMethod(risk.data)}
          peopleScored={risk.data ? risk.data.length : null}
          riskFailed={Boolean(risk.error)}
          communityCount={communities.data ? communities.data.length : null}
          communitiesFailed={Boolean(communities.error)}
          anomalyExtreme={anomalies.data?.distribution.EXTREME ?? null}
          anomalyHigh={anomalies.data?.distribution.HIGH ?? null}
          anomaliesFailed={Boolean(anomalies.error)}
          lastRefreshedAt={lastRefreshedAt}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <TopPrioritiesPanel
          keyPersons={keyPersons.data}
          riskProfiles={risk.data}
          isLoading={keyPersons.isLoading}
          error={keyPersons.error}
          onRetry={keyPersons.refetch}
          riskUnavailable={Boolean(risk.error) && !risk.data}
        />

        <CommunityOverviewPanel
          communities={communities.data}
          isLoading={communities.isLoading}
          error={communities.error}
          onRetry={communities.refetch}
        />
      </div>
    </div>
  )
}
