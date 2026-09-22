import type { GraphIndex, ActivePath, PathHop } from '@/types'
import type { Neo4jPathFound } from '@/types'

/** Map a Neo4j path response onto the loaded graph index for canvas highlighting. */
export function resolveNeo4jPath(
  path: Neo4jPathFound,
  index: GraphIndex,
): ActivePath {
  const nodeIds = path.nodes.map((node) => node.id)
  const edgeIds = new Set<string>()

  const hops: PathHop[] = path.relationships.map((rel) => {
    const exactId = `${rel.source}|${rel.type}|${rel.target}`
    if (index.edgesById.has(exactId)) {
      edgeIds.add(exactId)
    } else {
      for (const edge of index.edges) {
        const forward = edge.source === rel.source && edge.target === rel.target
        const backward = edge.source === rel.target && edge.target === rel.source
        if (forward || backward) edgeIds.add(edge.id)
      }
    }

    return {
      from: rel.source,
      to: rel.target,
      relationship: rel.type,
    }
  })

  return {
    sourceId: path.source_id,
    targetId: path.target_id,
    degrees: Math.max(nodeIds.length - 1, 0),
    nodeIds,
    hops,
    edgeIds,
  }
}
