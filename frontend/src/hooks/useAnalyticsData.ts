import { useCallback } from 'react'

import {
  ANALYTICS_RANK_LIMIT,
  sortByBetweenness,
  sortByPageRank,
  sortByRiskScore,
} from '@/lib/analytics'
import {
  anomaliesResource,
  fetchCentrality,
  fetchNetworkStatistics,
  getCommunities,
  getRiskScores,
} from '@/services'
import type {
  AnomalyResponse,
  CentralityResult,
  Community,
  NetworkStatistics,
  RiskProfile,
} from '@/types'
import { useAsyncResource } from './useAsyncResource'
import type { AsyncResource } from './useAsyncResource'

export interface AnalyticsData {
  statistics: AsyncResource<NetworkStatistics>
  centrality: AsyncResource<CentralityResult[]>
  communities: AsyncResource<Community[]>
  risk: AsyncResource<RiskProfile[]>
  anomalies: AsyncResource<AnomalyResponse>
  topByPageRank: CentralityResult[] | null
  topByBetweenness: CentralityResult[] | null
  highestRisk: RiskProfile[] | null
  isLoading: boolean
  lastRefreshedAt: Date | null
  refreshAll: () => void
}

/**
 * Loads all five analytics endpoints in parallel.
 *
 * Centrality and risk are sorted client-side for the ranked panels. Each
 * section keeps its own error state so one failing endpoint does not blank
 * the rest of the page.
 */
export function useAnalyticsData(): AnalyticsData {
  const statistics = useAsyncResource<NetworkStatistics>((options) =>
    fetchNetworkStatistics(options),
  )

  const centrality = useAsyncResource<CentralityResult[]>((options) =>
    fetchCentrality(options).then((response) => response.data),
  )

  const communities = useAsyncResource<Community[]>((options) =>
    getCommunities(options),
  )

  const risk = useAsyncResource<RiskProfile[]>((options) =>
    getRiskScores(options),
  )

  const anomalies = useAsyncResource<AnomalyResponse>((options) =>
    anomaliesResource.load(options),
  )

  const topByPageRank = centrality.data
    ? sortByPageRank(centrality.data).slice(0, ANALYTICS_RANK_LIMIT)
    : null

  const topByBetweenness = centrality.data
    ? sortByBetweenness(centrality.data).slice(0, ANALYTICS_RANK_LIMIT)
    : null

  const highestRisk = risk.data
    ? sortByRiskScore(risk.data).slice(0, ANALYTICS_RANK_LIMIT)
    : null

  const sections = [statistics, centrality, communities, risk, anomalies]
  const isLoading = sections.some((section) => section.isLoading)

  const settledTimes = sections
    .map((section) => section.settledAt?.getTime())
    .filter((time): time is number => time !== undefined)

  const lastRefreshedAt =
    settledTimes.length > 0 ? new Date(Math.max(...settledTimes)) : null

  const refetchStatistics = statistics.refetch
  const refetchCentrality = centrality.refetch
  const refetchCommunities = communities.refetch
  const refetchRisk = risk.refetch
  const refetchAnomalies = anomalies.refetch

  const refreshAll = useCallback(() => {
    anomaliesResource.invalidate()
    refetchStatistics()
    refetchCentrality()
    refetchCommunities()
    refetchRisk()
    refetchAnomalies()
  }, [
    refetchStatistics,
    refetchCentrality,
    refetchCommunities,
    refetchRisk,
    refetchAnomalies,
  ])

  return {
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
  }
}
