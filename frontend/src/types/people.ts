/**
 * View models for the People module.
 *
 * Everything here is derived from `/entities/persons`, `/analytics/centrality`,
 * `/analytics/risk` and `/network/graph`; no field is synthesised.
 */

import type {
  AnomalyProfile,
  CentralityResult,
  RiskLevel,
  RiskProfile,
} from './analytics'
import type { Person } from './entities'
import type { AggregatedEdge, GraphView } from './graph'
import type { NetworkEdge, NetworkNode, PersonNode } from './network'

/** `GET /analytics/risk/{person_id}` — one row of the `/analytics/risk` list. */
export type RiskResult = RiskProfile

/**
 * A 404 from the backend means "this id is not in the dataset", which the UI
 * must report differently from a transport failure.
 */
export type PersonLookup = { found: true; person: Person } | { found: false }

export type PersonRiskLookup =
  | { found: true; risk: RiskProfile }
  | { found: false }

/* -------------------------------------------------------------------------- */
/* Roster                                                                      */
/* -------------------------------------------------------------------------- */

/** One roster row: a person record joined with its risk and centrality. */
export interface PersonRosterRow {
  person: Person
  /** Null when `/analytics/risk` has no entry for this person. */
  riskScore: number | null
  riskLevel: RiskLevel | null
  /** Null when `/analytics/centrality` has no entry for this person. */
  pagerank: number | null
  betweenness: number | null
  /** Pre-lowered searchable text, so filtering never re-reads the record. */
  haystack: string
}

export const PEOPLE_SORT_KEYS = [
  'name',
  'person_id',
  'city',
  'risk',
  'pagerank',
  'betweenness',
] as const

export type PeopleSortKey = (typeof PEOPLE_SORT_KEYS)[number]

export type SortDirection = 'asc' | 'desc'

export interface PeopleSort {
  key: PeopleSortKey
  direction: SortDirection
}

/* -------------------------------------------------------------------------- */
/* Relationships                                                               */
/* -------------------------------------------------------------------------- */

/**
 * One aggregated link between the profiled person and a neighbouring entity.
 * Direction is preserved because "called" and "was called by" are different
 * investigative facts.
 */
export interface PersonRelationship {
  id: string
  relationship: string
  /** True when the profiled person is the edge source. */
  outgoing: boolean
  counterpartId: string
  /** Null only if the backend emitted an edge to a node it did not return. */
  counterpart: NetworkNode | null
  counterpartLabel: string
  counterpartDetail: string | null
  /** API edge records collapsed into this link. */
  count: number
  records: NetworkEdge[]
  /** Aggregated from the records, and null when they do not carry the field. */
  totalAmount: number | null
  totalDurationSeconds: number | null
  earliest: string | null
  latest: string | null
}

/** A neighbouring person, collapsed across every link between the two. */
export interface ConnectedPerson {
  entityId: string
  name: string
  homeCity: string | null
  riskGroup: string | null
  /** Underlying API edge records in either direction. */
  interactions: number
  /** Distinct relationship names linking the two, sorted. */
  relationships: string[]
}

/** One row of the connection summary. */
export interface RelationshipCount {
  relationship: string
  /** Underlying API edge records. */
  interactions: number
  /** Distinct counterparts reached by this relationship. */
  counterparts: number
}

/** A dated relationship record, for the activity list. */
export interface PersonActivityEvent {
  id: string
  /** Raw backend timestamp or date; sorted lexicographically (ISO-like). */
  at: string
  relationship: string
  outgoing: boolean
  counterpartId: string
  counterpartLabel: string
  amount: number | null
  durationSeconds: number | null
  callType: string | null
  /**
   * True when the date comes from the linked event node rather than the edge:
   * `INVOLVED_IN` and `OBSERVED_AT` edges carry no timestamp of their own.
   */
  fromEventNode: boolean
}

/* -------------------------------------------------------------------------- */
/* Profile                                                                     */
/* -------------------------------------------------------------------------- */

export interface PersonAssociations {
  vehicles: PersonRelationship[]
  crimeEvents: PersonRelationship[]
  surveillance: PersonRelationship[]
  connectedPeople: ConnectedPerson[]
  financial: PersonRelationship[]
  calls: PersonRelationship[]
  social: PersonRelationship[]
}

/** Local neighbourhood prepared for the mini graph. */
export interface PersonNeighbourhood {
  view: GraphView
  edges: AggregatedEdge[]
  /** Neighbours drawn. */
  shown: number
  /** Distinct neighbours in the graph, before capping. */
  total: number
}

/** Everything the profile derives from `/network/graph`. */
export interface PersonGraphContext {
  /** The person's own graph node, if the graph contains it. */
  node: PersonNode | null
  /** Distinct adjacent entities, ignoring direction. */
  directConnections: number
  relationshipCounts: RelationshipCount[]
  associations: PersonAssociations
  activity: PersonActivityEvent[]
  neighbourhood: PersonNeighbourhood
}

export interface PersonProfile {
  personId: string
  person: Person
  /** Null when `/analytics/risk/{id}` has no profile for this person. */
  risk: RiskProfile | null
  /** Null when `/analytics/anomalies/{id}` has no profile for this person. */
  anomaly: AnomalyProfile | null
  /** Null when `/analytics/centrality` has no entry for this person. */
  centrality: CentralityResult | null
  /** Null while `/network/graph` is loading or after it failed. */
  graph: PersonGraphContext | null
}
