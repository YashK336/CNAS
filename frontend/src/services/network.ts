import { http } from './api'
import type { RequestOptions } from './api'
import type { NetworkGraph, NetworkSummary } from '@/types'

export function fetchNetworkSummary(
  options?: RequestOptions,
): Promise<NetworkSummary> {
  return http.get<NetworkSummary>('/network/summary', options)
}

/** Full node/edge payload — expect a few thousand edges on the sample data. */
export function fetchNetworkGraph(
  options?: RequestOptions,
): Promise<NetworkGraph> {
  return http.get<NetworkGraph>('/network/graph', options)
}

export interface Neo4jGraphImportResult {
  status: string
  detail?: string
  nodes?: number
  relationships?: number
  nodes_merged?: number
  relationships_merged?: number
}

const GRAPH_IMPORT_TIMEOUT_MS = 300_000

/** Writes the canonical CNAS graph (including overlay rows) into Neo4j. */
export function triggerNeo4jImport(
  dryRun = false,
  options?: RequestOptions,
): Promise<Neo4jGraphImportResult> {
  const query = dryRun ? '?dry_run=true' : '?dry_run=false'
  return http.post<Neo4jGraphImportResult>(
    `/network/neo4j-import${query}`,
    {},
    { timeout: GRAPH_IMPORT_TIMEOUT_MS, ...options },
  )
}
