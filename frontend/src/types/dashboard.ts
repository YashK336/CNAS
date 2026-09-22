import type { RiskLevel } from './analytics'

/**
 * View models derived on the client from API responses. Nothing here is
 * fabricated — every field is computed from a FastAPI payload.
 */

export interface RiskDistributionBucket {
  level: RiskLevel
  count: number
  /** Share of scored people, 0-100. */
  percentage: number
}

export interface RiskDistribution {
  /** Number of people returned by /analytics/risk. */
  total: number
  /** Ordered CRITICAL -> LOW. */
  buckets: RiskDistributionBucket[]
}

/**
 * A person from /analytics/key-persons joined with their /analytics/risk
 * profile. Risk fields are null when the risk endpoint is unavailable or the
 * person has no profile.
 */
export interface InvestigativePriority {
  entity_id: string
  name: string | null
  degree_centrality: number
  betweenness_centrality: number
  pagerank: number
  risk_score: number | null
  risk_level: RiskLevel | null
  risk_reasons: string[]
}

/** Node mix derived from /analytics/statistics. */
export interface NetworkCompositionSlice {
  label: string
  count: number
  /** Share of total nodes, 0-100. */
  percentage: number
}
