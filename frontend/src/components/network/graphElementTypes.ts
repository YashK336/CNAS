import type { EdgeTypes, NodeTypes } from '@xyflow/react'

import {
  CrimeEventGraphNode,
  PersonGraphNode,
  SurveillanceGraphNode,
  VehicleGraphNode,
} from './GraphNodes'
import { RelationshipEdge } from './RelationshipEdge'

/**
 * React Flow re-creates its internal renderer whenever these objects change
 * identity, so they live at module scope in a file of their own.
 *
 * Node type names match `entity_type`, which is what the backend returns.
 */
export const GRAPH_NODE_TYPES: NodeTypes = {
  person: PersonGraphNode,
  vehicle: VehicleGraphNode,
  crime_event: CrimeEventGraphNode,
  surveillance_event: SurveillanceGraphNode,
}

export const GRAPH_EDGE_TYPES: EdgeTypes = {
  relationship: RelationshipEdge,
}
