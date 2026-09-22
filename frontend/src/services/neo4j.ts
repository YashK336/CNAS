import { http } from './api'
import type { RequestOptions } from './api'
import type {
  Neo4jCommunitiesResponse,
  Neo4jPageRankResponse,
  Neo4jPathResult,
  PersonRiskEvidenceResponse,
} from '../types/analytics'

/** Applied temporal window for Neo4j graph investigation and GDS analytics. */
export interface TemporalWindow {
  fromDatetime: string | null
  toDatetime: string | null
}

export function buildTemporalParams(
  window: TemporalWindow | null | undefined,
): Record<string, string> {
  const params: Record<string, string> = {}
  if (window?.fromDatetime) params.from_datetime = window.fromDatetime
  if (window?.toDatetime) params.to_datetime = window.toDatetime
  return params
}

function withQuery(path: string, params: Record<string, string | number>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    search.set(key, String(value))
  }
  const query = search.toString()
  return query ? `${path}?${query}` : path
}

export async function fetchNeo4jPageRank(
  window?: TemporalWindow | null,
  options?: RequestOptions,
): Promise<Neo4jPageRankResponse> {
  return http.get<Neo4jPageRankResponse>(
    withQuery('/analytics/neo4j/pagerank', buildTemporalParams(window)),
    options,
  )
}

export async function fetchNeo4jCommunities(
  window?: TemporalWindow | null,
  options?: RequestOptions,
): Promise<Neo4jCommunitiesResponse> {
  return http.get<Neo4jCommunitiesResponse>(
    withQuery('/analytics/neo4j/communities', buildTemporalParams(window)),
    options,
  )
}

export async function fetchNeo4jPersonPath(
  sourceId: string,
  targetId: string,
  window?: TemporalWindow | null,
  maxDepth = 6,
  options?: RequestOptions,
): Promise<Neo4jPathResult> {
  return http.get<Neo4jPathResult>(
    withQuery(
      `/analytics/neo4j/path/${encodeURIComponent(sourceId)}/${encodeURIComponent(targetId)}`,
      { max_depth: maxDepth, ...buildTemporalParams(window) },
    ),
    options,
  )
}

export async function fetchPersonRiskEvidence(
  personId: string,
  graphSeeds: string[],
  options?: RequestOptions,
): Promise<PersonRiskEvidenceResponse> {
  return http.get<PersonRiskEvidenceResponse>(
    withQuery(
      `/analytics/risk/${encodeURIComponent(personId)}/evidence`,
      { graph_seeds: graphSeeds.join(',') },
    ),
    options,
  )
}
