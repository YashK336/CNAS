/**
 * Graph shapes returned by `/network/*`.
 *
 * The backend serialises each node as `{ id, ...nodeAttributes }` and each edge
 * as `{ source, target, ...edgeAttributes }`, so the attribute sets differ by
 * `entity_type` / `relationship`.
 */

export const ENTITY_TYPES = [
  'person',
  'vehicle',
  'crime_event',
  'surveillance_event',
] as const

export type EntityType = (typeof ENTITY_TYPES)[number]

interface NetworkNodeBase {
  id: string
}

export interface PersonNode extends NetworkNodeBase {
  entity_type: 'person'
  name: string
  phone: string | null
  home_city: string | null
  risk_group: string | null
}

export interface VehicleNode extends NetworkNodeBase {
  entity_type: 'vehicle'
  registered_city: string | null
  vehicle_type: string | null
}

export interface CrimeEventNode extends NetworkNodeBase {
  entity_type: 'crime_event'
  crime: string
  date: string
  location: string | null
}

export interface SurveillanceEventNode extends NetworkNodeBase {
  entity_type: 'surveillance_event'
  location: string | null
  timestamp: string
  event_type: string
}

export type NetworkNode =
  | PersonNode
  | VehicleNode
  | CrimeEventNode
  | SurveillanceEventNode

/**
 * Social edges are emitted as `SOCIAL_<INTERACTION_TYPE>`, so the relationship
 * field stays open while still documenting the known values.
 */
export type RelationshipType =
  | 'OWNS'
  | 'CALLED'
  | 'TRANSFERRED_MONEY'
  | 'INVOLVED_IN'
  | 'OBSERVED_AT'
  | (string & {})

export interface NetworkEdge {
  source: string
  target: string
  relationship: RelationshipType
  /** Present on `CALLED` edges. */
  timestamp?: string
  duration?: number
  call_type?: string
  /** Present on `TRANSFERRED_MONEY` edges. */
  amount?: number
  /** Present on `TRANSFERRED_MONEY` and `SOCIAL_*` edges. */
  date?: string
}

/** `GET /network/graph`. */
export interface NetworkGraph {
  nodes: NetworkNode[]
  edges: NetworkEdge[]
}

/** `GET /network/summary`. */
export interface NetworkSummary {
  nodes: number
  edges: number
}
