import type { EntityType } from './network'

/** `GET /analytics/statistics`. */
export interface NetworkStatistics {
  nodes: number
  edges: number
  people: number
  vehicles: number
  crime_events: number
  surveillance_events: number
}

/** `GET /analytics/centrality` and `GET /analytics/key-persons`. */
export interface CentralityResult {
  entity_id: string
  name: string | null
  degree_centrality: number
  betweenness_centrality: number
  pagerank: number
}

export interface CommunityMember {
  entity_id: string
  name: string | null
}

/** `GET /analytics/communities`. */
export interface Community {
  community_id: number
  size: number
  members: CommunityMember[]
}

/** Current backend envelope. Older builds used `{ total, data }`. */
export interface CommunitiesResponse {
  total_communities: number
  communities: Community[]
}

export const RISK_LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const

export type RiskLevel = (typeof RISK_LEVELS)[number]

/**
 * Per-signal point contributions from the rule engine. Keys match
 * `RISK_WEIGHTS` in `backend/app/services/analytics.py`.
 */
export interface RiskSignalScores {
  network_influence: number
  fir_involvement: number
  financial_activity: number
  communication_activity: number
  social_activity: number
  surveillance_activity: number
  network_bridge_role: number
  graph_propagation?: number
}

export interface RiskRawActivity {
  communications: number
  financial_transactions: number
  social_interactions: number
  fir_involvement: number
  surveillance_events: number
}

/** `GET /analytics/risk` and `GET /analytics/risk/{person_id}`. */
export interface RiskProfile {
  entity_id: string
  name: string | null
  risk_score: number
  risk_level: RiskLevel
  scoring_method: string
  /** Current rule-engine payload. */
  signals?: RiskSignalScores
  raw_activity?: RiskRawActivity
  /** Older payload; omitted by the current scorer. */
  risk_reasons?: string[]
  signal_scores?: RiskSignalScores
  graph_seeds?: string[]
  personalized_pagerank?: number | null
  graph_contribution?: number | null
}

/** Optional time window echoed by Neo4j GDS analytics endpoints. */
export interface AnalyticsTimeWindow {
  from_datetime: string | null
  to_datetime: string | null
}

/** `GET /analytics/neo4j/pagerank`. */
export interface Neo4jPageRankEntry {
  entity_id: string
  name: string | null
  pagerank: number
  rank?: number
}

export interface Neo4jPageRankResponse {
  algorithm: string
  graph_name: string
  total: number
  time_window?: AnalyticsTimeWindow | null
  data: Neo4jPageRankEntry[]
}

/** `GET /analytics/neo4j/communities`. */
export interface Neo4jCommunityMember {
  entity_id: string
  name: string | null
}

export interface Neo4jCommunity {
  community_id: number
  display_id?: number
  size: number
  members: Neo4jCommunityMember[]
}

export interface Neo4jCommunitiesResponse {
  algorithm: string
  graph_name: string
  total_communities: number
  time_window?: AnalyticsTimeWindow | null
  communities: Neo4jCommunity[]
}

export interface RelationshipProvenance {
  source: string | null
  source_ref: string | null
  content_hash: string | null
  ingested_at: string | null
}

/** Relationship on a Neo4j path or risk evidence chain. */
export interface GraphPathRelationship {
  type: string
  source: string
  target: string
  provenance?: RelationshipProvenance | null
}

export interface GraphPathNode {
  entity_id: string
  entity_type: string | null
  name: string | null
}

/** Raw node from `GET /analytics/neo4j/path`. */
export interface Neo4jInvestigationNode {
  id: string
  labels?: string[]
  properties?: Record<string, unknown>
  provenance?: RelationshipProvenance | null
}

/** `GET /analytics/neo4j/path/{source}/{target}`. */
export interface Neo4jPathFound {
  found: true
  source_id: string
  target_id: string
  nodes: Neo4jInvestigationNode[]
  relationships: GraphPathRelationship[]
}

export interface Neo4jPathNotFound {
  found: false
  message: string
}

export type Neo4jPathResult = Neo4jPathFound | Neo4jPathNotFound

export interface GraphPropagationEvidence {
  seed_id: string
  found: boolean
  degrees_of_separation?: number
  nodes?: GraphPathNode[]
  relationships?: GraphPathRelationship[]
  message?: string
}

/** `GET /analytics/risk/{person_id}/evidence`. */
export interface PersonRiskEvidenceResponse {
  entity_id: string
  graph_seeds: string[]
  evidence: {
    graph_propagation: GraphPropagationEvidence[]
  }
}

export interface ConnectionPathNode {
  entity_id: string
  entity_type: EntityType | null
  name: string | null
  location: string | null
}

export interface ConnectionPathEdge {
  source: string
  target: string
  relationship: string | null
}

export interface ConnectionFound {
  found: true
  source: string
  target: string
  degrees_of_separation: number
  nodes: ConnectionPathNode[]
  relationships: ConnectionPathEdge[]
}

export interface ConnectionNotFound {
  found: false
  message: string
}

/** `GET /analytics/connection/{source_id}/{target_id}`. */
export type ConnectionResult = ConnectionFound | ConnectionNotFound

export const ANOMALY_LEVELS = [
  'NORMAL',
  'ELEVATED',
  'HIGH',
  'EXTREME',
] as const

export type AnomalyLevel = (typeof ANOMALY_LEVELS)[number]

export interface AnomalyFeatureScores {
  communication: number
  financial: number
  social: number
  surveillance: number
}

export interface AnomalyActivity {
  communications: number
  financial_transactions: number
  social_interactions: number
  surveillance_events: number
}

/** One person from `GET /analytics/anomalies`. */
export interface AnomalyProfile {
  entity_id: string
  name: string | null
  anomaly_score: number
  anomaly_level: AnomalyLevel
  feature_scores: AnomalyFeatureScores
  activity: AnomalyActivity
  reasons: string[]
  method: string
}

/** Band counts from `GET /analytics/anomalies`. */
export interface AnomalyDistribution {
  NORMAL: number
  ELEVATED: number
  HIGH: number
  EXTREME: number
}

/** Envelope of `GET /analytics/anomalies`. */
export interface AnomalyResponse {
  total: number
  distribution: AnomalyDistribution
  data: AnomalyProfile[]
}

export type PersonAnomalyLookup =
  | { found: true; anomaly: AnomalyProfile }
  | { found: false }

export interface An2FindingEvidence {
  source: string
  source_ref: string
  record_id: string
  content_hash: string
  ingested_at: string
  jurisdiction: string
  case_ref: string
  identifier_type: string
  identifier_value: string
  source_text: string | null
  extraction_method: string | null
  resolution_status: string | null
  matched_entity_id: string | null
  confidence: number
  valid_from: string | null
  valid_to: string | null
}

export interface An2Finding {
  finding_id: string
  finding_type: 'AN-2'
  claim: string
  identifier: { type: string; value: string }
  cases: string[]
  jurisdictions: string[]
  evidence: An2FindingEvidence[]
  method: {
    name: string
    min_distinct_cases: number
    min_jurisdictions: number
    deduplication_key: string
  }
  confidence: number
  limits: string[]
  matched_entity_ids: string[]
  valid_from: string | null
  valid_to: string | null
}

export interface An2FindingsResponse {
  finding_type: 'AN-2'
  total: number
  data: An2Finding[]
}
