import { useCallback, useMemo, useSyncExternalStore } from 'react'

import {
  fetchNetworkSummary,
  getCommunities,
  getImportedDatasetGeneration,
  networkGraphResource,
  subscribeImportedDatasets,
} from '@/services'
import { buildGraphIndex } from '@/lib/graph'
import type {
  Community,
  GraphIndex,
  NetworkGraph,
  NetworkSummary,
} from '@/types'
import { useAsyncResource } from './useAsyncResource'
import type { AsyncResource } from './useAsyncResource'

export interface NetworkGraphData {
  graph: AsyncResource<NetworkGraph>
  summary: AsyncResource<NetworkSummary>
  communities: AsyncResource<Community[]>
  /** Derived once per payload; null until the graph has loaded. */
  index: GraphIndex | null
  reload: () => void
}

/**
 * Loads the explorer's data from the shared session graph cache. AppShell keeps
 * this hook mounted, so import invalidation must change `datasetGeneration` or
 * the canvas would keep the pre-import payload.
 */
export function useNetworkGraph(): NetworkGraphData {
  const datasetGeneration = useSyncExternalStore(
    subscribeImportedDatasets,
    getImportedDatasetGeneration,
    getImportedDatasetGeneration,
  )

  const graph = useAsyncResource<NetworkGraph>(
    (options) => networkGraphResource.load(options),
    [datasetGeneration],
  )

  const summary = useAsyncResource<NetworkSummary>(
    (options) => fetchNetworkSummary(options),
    [datasetGeneration],
  )

  const communities = useAsyncResource<Community[]>(
    (options) => getCommunities(options),
    [datasetGeneration],
  )

  const index = useMemo(
    () => (graph.data ? buildGraphIndex(graph.data) : null),
    [graph.data],
  )

  const refetchGraph = graph.refetch
  const refetchSummary = summary.refetch
  const refetchCommunities = communities.refetch

  const reload = useCallback(() => {
    networkGraphResource.invalidate()
    refetchGraph()
    refetchSummary()
    refetchCommunities()
  }, [refetchGraph, refetchSummary, refetchCommunities])

  return { graph, summary, communities, index, reload }
}
