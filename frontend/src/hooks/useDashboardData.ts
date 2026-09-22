import { useCallback } from 'react'

import {
  fetchKeyPersons,
  fetchNetworkStatistics,
  fetchNetworkSummary,
  getCommunities,
  getRiskScores,
  anomaliesResource,
} from '@/services'
import type {
  AnomalyResponse,
  CentralityResult,
  Community,
  NetworkStatistics,
  NetworkSummary,
  RiskProfile,
} from '@/types'
import { useAsyncResource } from './useAsyncResource'
import type { AsyncResource } from './useAsyncResource'

export type ApiReachability = 'checking' | 'online' | 'degraded' | 'offline'
export type NetworkAvailability = 'loading' | 'loaded' | 'unavailable'

export interface DashboardData {
  statistics: AsyncResource<NetworkStatistics>
  risk: AsyncResource<RiskProfile[]>
  keyPersons: AsyncResource<CentralityResult[]>
  communities: AsyncResource<Community[]>
  networkSummary: AsyncResource<NetworkSummary>
  anomalies: AsyncResource<AnomalyResponse>
  /** True while any section is still in flight. */
  isLoading: boolean
  /** Derived from the actual outcomes of the requests above. */
  apiReachability: ApiReachability
  networkAvailability: NetworkAvailability
  /** Most recent moment any section settled. */
  lastRefreshedAt: Date | null
  refreshAll: () => void
}

/**
 * Loads every dashboard section.
 *
 * Each section owns its own request so a single failing endpoint degrades one
 * panel instead of the page, and can be retried on its own. All five requests
 * are issued together on mount, so they run concurrently. `/analytics/risk` is
 * fetched once and shared by the risk distribution and the priorities join —
 * the backend rebuilds the graph per call, so duplicate requests are costly.
 */
export function useDashboardData(): DashboardData {
  const statistics = useAsyncResource<NetworkStatistics>((options) =>
    fetchNetworkStatistics(options),
  )

  const risk = useAsyncResource<RiskProfile[]>((options) =>
    getRiskScores(options),
  )

  const keyPersons = useAsyncResource<CentralityResult[]>((options) =>
    fetchKeyPersons(options).then((response) => response.data),
  )

  const communities = useAsyncResource<Community[]>((options) =>
    getCommunities(options),
  )

  const networkSummary = useAsyncResource<NetworkSummary>((options) =>
    fetchNetworkSummary(options),
  )

  const anomalies = useAsyncResource<AnomalyResponse>((options) =>
    anomaliesResource.load(options),
  )

  const sections = [statistics, risk, keyPersons, communities, networkSummary]

  const isLoading =
    sections.some((section) => section.isLoading) || anomalies.isLoading
  const succeeded = sections.filter((section) => section.data !== null).length
  const failed = sections.filter((section) => section.error !== null).length

  let apiReachability: ApiReachability = 'checking'
  if (succeeded > 0) {
    apiReachability = failed > 0 ? 'degraded' : 'online'
  } else if (failed > 0) {
    apiReachability = 'offline'
  }

  let networkAvailability: NetworkAvailability = 'loading'
  if (networkSummary.data) {
    networkAvailability = 'loaded'
  } else if (networkSummary.error) {
    networkAvailability = 'unavailable'
  }

  const settledTimes = sections
    .map((section) => section.settledAt?.getTime())
    .filter((time): time is number => time !== undefined)

  const lastRefreshedAt =
    settledTimes.length > 0 ? new Date(Math.max(...settledTimes)) : null

  // `refetch` is referentially stable per resource, so bind the callbacks
  // directly rather than depending on the whole resource objects.
  const refetchStatistics = statistics.refetch
  const refetchRisk = risk.refetch
  const refetchKeyPersons = keyPersons.refetch
  const refetchCommunities = communities.refetch
  const refetchNetworkSummary = networkSummary.refetch
  const refetchAnomalies = anomalies.refetch

  const refreshAll = useCallback(() => {
    anomaliesResource.invalidate()
    refetchStatistics()
    refetchRisk()
    refetchKeyPersons()
    refetchCommunities()
    refetchNetworkSummary()
    refetchAnomalies()
  }, [
    refetchStatistics,
    refetchRisk,
    refetchKeyPersons,
    refetchCommunities,
    refetchNetworkSummary,
    refetchAnomalies,
  ])

  return {
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
  }
}
