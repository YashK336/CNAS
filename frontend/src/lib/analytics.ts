/**
 * Pure derivations for the Analytics page.
 * Every value traces back to a FastAPI analytics payload.
 */

import type { CentralityResult, RiskProfile } from '@/types'

export const ANALYTICS_RANK_LIMIT = 10

export function sortByPageRank(
  results: CentralityResult[],
): CentralityResult[] {
  return [...results].sort((a, b) => b.pagerank - a.pagerank)
}

export function sortByBetweenness(
  results: CentralityResult[],
): CentralityResult[] {
  return [...results].sort(
    (a, b) => b.betweenness_centrality - a.betweenness_centrality,
  )
}

export function sortByDegree(
  results: CentralityResult[],
): CentralityResult[] {
  return [...results].sort((a, b) => b.degree_centrality - a.degree_centrality)
}

/** Highest risk score first. Backend order is not guaranteed. */
export function sortByRiskScore(profiles: RiskProfile[]): RiskProfile[] {
  return [...profiles].sort((a, b) => b.risk_score - a.risk_score)
}
