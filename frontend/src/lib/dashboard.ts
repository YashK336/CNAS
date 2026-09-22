import type {
  CentralityResult,
  Community,
  InvestigativePriority,
  NetworkCompositionSlice,
  NetworkStatistics,
  RiskDistribution,
  RiskProfile,
} from '@/types'

function share(count: number, total: number): number {
  return total > 0 ? (count / total) * 100 : 0
}

/** Counts people per risk level from `GET /analytics/risk`, CRITICAL → LOW. */
export function buildRiskDistribution(
  profiles: RiskProfile[],
): RiskDistribution {
  const critical = profiles.filter(
    (person) => person.risk_level === 'CRITICAL',
  ).length
  const high = profiles.filter((person) => person.risk_level === 'HIGH').length
  const medium = profiles.filter(
    (person) => person.risk_level === 'MEDIUM',
  ).length
  const low = profiles.filter((person) => person.risk_level === 'LOW').length

  const total = profiles.length
  const percentage = (count: number) => share(count, total)

  return {
    total,
    buckets: [
      { level: 'CRITICAL', count: critical, percentage: percentage(critical) },
      { level: 'HIGH', count: high, percentage: percentage(high) },
      { level: 'MEDIUM', count: medium, percentage: percentage(medium) },
      { level: 'LOW', count: low, percentage: percentage(low) },
    ],
  }
}

/**
 * Joins the centrality-ranked key persons with their risk profiles by
 * `entity_id`. The backend ranking order is preserved.
 */
export function joinInvestigativePriorities(
  keyPersons: CentralityResult[],
  profiles: RiskProfile[] | null,
): InvestigativePriority[] {
  const riskByEntityId = new Map<string, RiskProfile>(
    (profiles ?? []).map((profile) => [profile.entity_id, profile]),
  )

  return keyPersons.map((person) => {
    const risk = riskByEntityId.get(person.entity_id)

    return {
      entity_id: person.entity_id,
      name: person.name,
      degree_centrality: person.degree_centrality,
      betweenness_centrality: person.betweenness_centrality,
      pagerank: person.pagerank,
      risk_score: risk?.risk_score ?? null,
      risk_level: risk?.risk_level ?? null,
      risk_reasons: risk?.risk_reasons ?? [],
    }
  })
}

/** Node mix, as a share of the total node count reported by the backend. */
export function buildNetworkComposition(
  statistics: NetworkStatistics,
): NetworkCompositionSlice[] {
  const entries: { label: string; count: number }[] = [
    { label: 'People', count: statistics.people },
    { label: 'Vehicles', count: statistics.vehicles },
    { label: 'Crime events', count: statistics.crime_events },
    { label: 'Surveillance', count: statistics.surveillance_events },
  ]

  return entries.map((entry) => ({
    ...entry,
    percentage: share(entry.count, statistics.nodes),
  }))
}

/** Largest first. The backend already sorts, this keeps it explicit. */
export function sortCommunitiesBySize(communities: Community[]): Community[] {
  return [...communities].sort((a, b) => b.size - a.size)
}

/** The scoring engine reported by the risk endpoint, e.g. "rules_v1". */
export function readScoringMethod(
  profiles: RiskProfile[] | null,
): string | null {
  return profiles?.[0]?.scoring_method ?? null
}
