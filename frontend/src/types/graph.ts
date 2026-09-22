import type { EntityType, NetworkEdge, NetworkNode } from './network'

/** Plain coordinate, so graph maths stays free of React Flow imports. */
export interface Point {
  x: number
  y: number
}

/**
 * One `(source, target, relationship)` group from the backend MultiDiGraph.
 * The underlying records are kept verbatim so nothing from the API is lost.
 */
export interface AggregatedEdge {
  id: string
  source: string
  target: string
  relationship: string
  /** How many API edges collapsed into this one. */
  count: number
  records: NetworkEdge[]
  /** Index among the parallel edges of this ordered pair, for curve offsets. */
  parallelIndex: number
  parallelCount: number
}

/** Everything derived once from `GET /network/graph`. */
export interface GraphIndex {
  nodes: NetworkNode[]
  nodesById: Map<string, NetworkNode>
  edges: AggregatedEdge[]
  edgesById: Map<string, AggregatedEdge>
  /** Aggregated edges touching a node, either direction. */
  edgesByNode: Map<string, AggregatedEdge[]>
  /** Distinct adjacent entities, ignoring direction. */
  neighborsById: Map<string, Set<string>>
  /** Relationship names present in the data, sorted. */
  relationshipTypes: string[]
  /** Underlying API edge count per relationship. */
  relationshipCounts: Map<string, number>
  entityTypeCounts: Record<EntityType, number>
  /** Deterministic ring order for people, strongly linked ones adjacent. */
  personOrder: string[]
  /** Non-person nodes grouped by the person they hang off. */
  satellitesByOwner: Map<string, string[]>
  /** Non-person nodes with no person neighbour. */
  unattachedNodes: string[]
}

export interface GraphFilters {
  entityTypes: ReadonlySet<EntityType>
  relationships: ReadonlySet<string>
}

export type PathRole = 'source' | 'step' | 'target'

/** A node prepared for rendering. */
export interface GraphViewNode {
  id: string
  entity: NetworkNode
  position: Point
  primary: string
  secondary: string | null
  selected: boolean
  dimmed: boolean
  pathRole: PathRole | null
  inCommunity: boolean
  /** Immediate neighbour of the selected node. */
  inNeighborhood: boolean
  /** When to show the entity name on the canvas. */
  labelPriority: 'always' | 'zoom' | 'hidden'
  size: { width: number; height: number }
}

export type EdgeEmphasis = 'normal' | 'dimmed' | 'active'

/** An aggregated edge prepared for rendering. */
export interface GraphViewEdge {
  id: string
  source: string
  target: string
  relationship: string
  count: number
  /** Perpendicular offset that separates parallel relationships. */
  curveOffset: number
  emphasis: EdgeEmphasis
  /** Relationship labels are reserved for path hops and the selected edge. */
  showLabel: boolean
}

export interface GraphView {
  nodes: GraphViewNode[]
  edges: GraphViewEdge[]
}

/** What the inspector is currently describing. */
export type GraphSelection =
  | { kind: 'node'; id: string }
  | { kind: 'edge'; id: string }

/** Option shown in the graph search and the trace selectors. */
export interface EntityOption {
  id: string
  label: string
  detail: string
  entityType: EntityType
}

/** One hop of a traced connection. */
export interface PathHop {
  from: string
  to: string
  relationship: string | null
}

/** Active trace, resolved against the loaded graph. */
export interface ActivePath {
  sourceId: string
  targetId: string
  degrees: number
  nodeIds: string[]
  hops: PathHop[]
  /** Aggregated-edge ids that make up the path. */
  edgeIds: Set<string>
}

export type TraceState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'found'; path: ActivePath }
  | { status: 'not-found'; message: string }
  | { status: 'error'; message: string }
