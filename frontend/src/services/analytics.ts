import { ApiError, http } from './api'
import type { RequestOptions } from './api'
import type {
  AnomalyProfile,
  AnomalyResponse,
  An2FindingsResponse,
  CentralityResult,
  Community,
  ConnectionResult,
  ListResponse,
  NetworkStatistics,
  PersonAnomalyLookup,
  PersonRiskLookup,
  RiskProfile,
} from '@/types'

export interface UnstructuredFirFindingInput {
  source: string
  source_ref: string
  jurisdiction: string
  text: string
  metadata?: Record<string, unknown>
}

export function fetchNetworkStatistics(
  options?: RequestOptions,
): Promise<NetworkStatistics> {
  return http.get<NetworkStatistics>('/analytics/statistics', options)
}

export function fetchCentrality(
  options?: RequestOptions,
): Promise<ListResponse<CentralityResult>> {
  return http.get<ListResponse<CentralityResult>>(
    '/analytics/centrality',
    options,
  )
}

/** Same shape as centrality, truncated to the top ranked entities. */
export function fetchKeyPersons(
  options?: RequestOptions,
): Promise<ListResponse<CentralityResult>> {
  return http.get<ListResponse<CentralityResult>>(
    '/analytics/key-persons',
    options,
  )
}

/** Graph rebuilds plus Louvain make this slower than a simple list. */
const COMMUNITY_REQUEST_TIMEOUT_MS = 120_000

function unwrapCommunities(payload: unknown): Community[] {
  if (Array.isArray(payload)) return payload as Community[]
  if (!payload || typeof payload !== 'object') return []

  const record = payload as Record<string, unknown>

  if (Array.isArray(record.communities)) {
    return record.communities as Community[]
  }

  if (Array.isArray(record.data)) {
    return record.data as Community[]
  }

  if (record.data && typeof record.data === 'object') {
    return unwrapCommunities(record.data)
  }

  return []
}

export async function getCommunities(
  options?: RequestOptions,
): Promise<Community[]> {
  const payload = await http.get<unknown>('/analytics/communities', {
    ...options,
    timeout: options?.timeout ?? COMMUNITY_REQUEST_TIMEOUT_MS,
  })
  return unwrapCommunities(payload)
}

export function fetchCommunities(
  options?: RequestOptions,
): Promise<ListResponse<Community>> {
  return getCommunities(options).then((communities) => ({
    total: communities.length,
    data: communities,
  }))
}

export function fetchConnection(
  sourceId: string,
  targetId: string,
  options?: RequestOptions,
): Promise<ConnectionResult> {
  return http.get<ConnectionResult>(
    `/analytics/connection/${encodeURIComponent(sourceId)}/${encodeURIComponent(targetId)}`,
    options,
  )
}

/** Envelope from `GET /analytics/risk`. Graph rebuilds make this slow. */
const RISK_REQUEST_TIMEOUT_MS = 120_000

export function fetchRiskProfiles(
  options?: RequestOptions,
): Promise<ListResponse<RiskProfile>> {
  return http.get<ListResponse<RiskProfile>>('/analytics/risk', {
    ...options,
    timeout: options?.timeout ?? RISK_REQUEST_TIMEOUT_MS,
  })
}

/**
 * People scored by the rule engine. Dashboard counts are derived from this
 * list — never from hardcoded band totals.
 */
export async function getRiskScores(
  options?: RequestOptions,
): Promise<RiskProfile[]> {
  const response = await fetchRiskProfiles(options)
  return response.data
}

export function fetchPersonRisk(
  personId: string,
  options?: RequestOptions,
): Promise<RiskProfile> {
  return http.get<RiskProfile>(
    `/analytics/risk/${encodeURIComponent(personId)}`,
    {
      ...options,
      timeout: options?.timeout ?? RISK_REQUEST_TIMEOUT_MS,
    },
  )
}

/**
 * `fetchPersonRisk` variant that turns the backend's 404 into a value. The rule
 * engine only scores person nodes, so an unscored id is an expected outcome
 * rather than a failure.
 */
export function lookupPersonRisk(
  personId: string,
  options?: RequestOptions,
): Promise<PersonRiskLookup> {
  return fetchPersonRisk(personId, options).then(
    (risk): PersonRiskLookup => ({ found: true, risk }),
    (error: unknown): PersonRiskLookup => {
      if (error instanceof ApiError && error.status === 404) {
        return { found: false }
      }
      throw error
    },
  )
}

export function fetchAnomalies(
  options?: RequestOptions,
): Promise<AnomalyResponse> {
  return http.get<AnomalyResponse>('/analytics/anomalies', {
    ...options,
    timeout: options?.timeout ?? RISK_REQUEST_TIMEOUT_MS,
  })
}

export function fetchPersonAnomaly(
  personId: string,
  options?: RequestOptions,
): Promise<AnomalyProfile> {
  return http.get<AnomalyProfile>(
    `/analytics/anomalies/${encodeURIComponent(personId)}`,
    {
      ...options,
      timeout: options?.timeout ?? RISK_REQUEST_TIMEOUT_MS,
    },
  )
}

export function lookupPersonAnomaly(
  personId: string,
  options?: RequestOptions,
): Promise<PersonAnomalyLookup> {
  return fetchPersonAnomaly(personId, options).then(
    (anomaly): PersonAnomalyLookup => ({ found: true, anomaly }),
    (error: unknown): PersonAnomalyLookup => {
      if (error instanceof ApiError && error.status === 404) {
        return { found: false }
      }
      throw error
    },
  )
}

export function fetchAn2Findings(
  records: UnstructuredFirFindingInput[],
  options?: RequestOptions,
): Promise<An2FindingsResponse> {
  return http.post<An2FindingsResponse>('/analytics/findings/an-2', records, options)
}
