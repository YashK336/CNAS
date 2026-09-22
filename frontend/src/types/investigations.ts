/** Saved Network Explorer investigation state from `/investigations`. */

export interface SavedInvestigation {
  id: string
  name: string
  description: string | null
  selected_entity_ids: string[]
  graph_seeds: string[]
  from_datetime: string | null
  to_datetime: string | null
  created_by: string | null
  jurisdiction: string | null
  created_at: string
  updated_at: string
}

export interface SavedInvestigationListResponse {
  total: number
  data: SavedInvestigation[]
}

export interface SavedInvestigationInput {
  name: string
  description?: string | null
  selected_entity_ids?: string[]
  graph_seeds?: string[]
  from_datetime?: string | null
  to_datetime?: string | null
  jurisdiction?: string | null
}

export interface SavedInvestigationUpdateInput {
  name?: string
  description?: string | null
  selected_entity_ids?: string[]
  graph_seeds?: string[]
  from_datetime?: string | null
  to_datetime?: string | null
}

/** Snapshot captured from the Network Explorer workspace. */
export interface NetworkExplorerSnapshot {
  selectedEntityIds: string[]
  graphSeeds: string[]
  fromDatetime: string | null
  toDatetime: string | null
  traceSourceId: string | null
  traceTargetId: string | null
  selectedNodeId: string | null
}
