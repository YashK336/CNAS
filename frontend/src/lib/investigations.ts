import type {
  NetworkExplorerSnapshot,
  SavedInvestigation,
} from '@/types'

/** Collect the current Network Explorer workspace into a save payload. */
export function buildNetworkExplorerSnapshot(input: {
  sourceId: string | null
  targetId: string | null
  selectionNodeId: string | null
  fromDatetime: string | null
  toDatetime: string | null
  graphSeeds?: string[]
}): NetworkExplorerSnapshot {
  const selectedEntityIds = Array.from(
    new Set(
      [
        input.selectionNodeId,
        input.sourceId,
        input.targetId,
      ].filter((value): value is string => Boolean(value)),
    ),
  )

  const graphSeeds =
    input.graphSeeds && input.graphSeeds.length > 0
      ? input.graphSeeds
      : input.sourceId
        ? [input.sourceId]
        : []

  return {
    selectedEntityIds,
    graphSeeds,
    fromDatetime: input.fromDatetime,
    toDatetime: input.toDatetime,
    traceSourceId: input.sourceId,
    traceTargetId: input.targetId,
    selectedNodeId: input.selectionNodeId,
  }
}

/** Apply a saved investigation onto Network Explorer state setters. */
export function applySavedInvestigation(
  investigation: SavedInvestigation,
): NetworkExplorerSnapshot {
  const ids = investigation.selected_entity_ids
  const traceSourceId = ids[0] ?? null
  const traceTargetId = ids.length > 1 ? (ids[1] ?? null) : null
  const selectedNodeId =
    ids.find(
      (entityId) => entityId !== traceSourceId && entityId !== traceTargetId,
    ) ??
    traceSourceId ??
    null

  return {
    selectedEntityIds: ids,
    graphSeeds: investigation.graph_seeds,
    fromDatetime: investigation.from_datetime,
    toDatetime: investigation.to_datetime,
    traceSourceId,
    traceTargetId,
    selectedNodeId,
  }
}

export function toDatetimeLocalValue(value: string | null | undefined): string {
  if (!value) return ''
  return value.slice(0, 16)
}

export function snapshotToInvestigationInput(
  snapshot: NetworkExplorerSnapshot,
  name: string,
  description?: string | null,
  jurisdiction?: string | null,
) {
  return {
    name,
    description: description ?? null,
    selected_entity_ids: snapshot.selectedEntityIds,
    graph_seeds: snapshot.graphSeeds,
    from_datetime: snapshot.fromDatetime,
    to_datetime: snapshot.toDatetime,
    jurisdiction: jurisdiction ?? null,
  }
}
