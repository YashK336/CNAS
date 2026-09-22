import { ENTITY_TYPES } from '@/types'
import type {
  ActivePath,
  AggregatedEdge,
  ConnectionFound,
  EdgeEmphasis,
  EntityOption,
  EntityType,
  GraphFilters,
  GraphIndex,
  GraphSelection,
  GraphView,
  GraphViewEdge,
  GraphViewNode,
  NetworkEdge,
  NetworkGraph,
  NetworkNode,
  PathRole,
  Point,
} from '@/types'

/* -------------------------------------------------------------------------- */
/* Attribute helpers                                                           */
/* -------------------------------------------------------------------------- */

/**
 * The datasets come from CSV via pandas, so a missing cell can surface as an
 * empty string or the string "nan" rather than JSON null.
 */
export function cleanValue(value: unknown): string | null {
  if (value === null || value === undefined) return null

  const text = String(value).trim()
  if (text === '') return null

  const lowered = text.toLowerCase()
  if (lowered === 'nan' || lowered === 'none' || lowered === 'null') return null

  return text
}

export function entityPrimaryLabel(node: NetworkNode): string {
  if (node.entity_type === 'person') return cleanValue(node.name) ?? node.id
  return node.id
}

export function entitySecondaryLabel(node: NetworkNode): string | null {
  switch (node.entity_type) {
    case 'person':
      return node.id
    case 'vehicle':
      return cleanValue(node.vehicle_type)
    case 'crime_event':
      return cleanValue(node.crime)
    case 'surveillance_event':
      return cleanValue(node.event_type)
  }
}

export interface EntityAttribute {
  label: string
  value: string
  mono?: boolean
}

/** Inspector rows for an entity. Fields the backend left empty are dropped. */
export function entityAttributes(node: NetworkNode): EntityAttribute[] {
  const rows: (EntityAttribute | null)[] = []

  const push = (label: string, value: unknown, mono = false) => {
    const cleaned = cleanValue(value)
    rows.push(cleaned === null ? null : { label, value: cleaned, mono })
  }

  switch (node.entity_type) {
    case 'person':
      push('Name', node.name)
      push('Person ID', node.id, true)
      push('Phone', node.phone, true)
      push('Home city', node.home_city)
      push('Risk group', node.risk_group)
      break
    case 'vehicle':
      push('Vehicle number', node.id, true)
      push('Vehicle type', node.vehicle_type)
      push('Registered city', node.registered_city)
      break
    case 'crime_event':
      push('Event ID', node.id, true)
      push('Crime', node.crime)
      push('Date', node.date, true)
      push('Location', node.location)
      break
    case 'surveillance_event':
      push('Event ID', node.id, true)
      push('Event type', node.event_type)
      push('Location', node.location)
      push('Timestamp', node.timestamp, true)
      break
  }

  return rows.filter((row): row is EntityAttribute => row !== null)
}

/* -------------------------------------------------------------------------- */
/* Index construction                                                          */
/* -------------------------------------------------------------------------- */

const SATELLITE_TYPE_ORDER: EntityType[] = [
  'vehicle',
  'crime_event',
  'surveillance_event',
]

/** Perpendicular spacing between parallel relationships of the same pair. */
const CURVE_STEP = 26

function pairKey(a: string, b: string): string {
  return a <= b ? `${a}::${b}` : `${b}::${a}`
}

function aggregateEdges(edges: NetworkEdge[]): AggregatedEdge[] {
  const groups = new Map<string, AggregatedEdge>()

  for (const record of edges) {
    const relationship = record.relationship || 'RELATED_TO'
    const id = `${record.source}|${relationship}|${record.target}`
    const existing = groups.get(id)

    if (existing) {
      existing.count += 1
      existing.records.push(record)
      continue
    }

    groups.set(id, {
      id,
      source: record.source,
      target: record.target,
      relationship,
      count: 1,
      records: [record],
      parallelIndex: 0,
      parallelCount: 1,
    })
  }

  const aggregated = [...groups.values()]

  // Separate parallel relationships per unordered pair, so both directions and
  // every relationship type between two entities stay individually visible.
  const byPair = new Map<string, AggregatedEdge[]>()
  for (const edge of aggregated) {
    const key = pairKey(edge.source, edge.target)
    const bucket = byPair.get(key)
    if (bucket) bucket.push(edge)
    else byPair.set(key, [edge])
  }

  for (const bucket of byPair.values()) {
    bucket.sort(
      (a, b) =>
        a.relationship.localeCompare(b.relationship) ||
        a.source.localeCompare(b.source),
    )

    bucket.forEach((edge, index) => {
      edge.parallelIndex = index
      edge.parallelCount = bucket.length
    })
  }

  return aggregated
}

/**
 * Orders people so that strongly connected ones end up adjacent on the ring:
 * greedy nearest-neighbour over aggregated interaction weights, seeded from the
 * busiest person. Fully deterministic, including tie-breaks.
 */
function seriatePeople(
  personIds: string[],
  weights: Map<string, Map<string, number>>,
): string[] {
  const sorted = [...personIds].sort((a, b) => a.localeCompare(b))
  if (sorted.length <= 2) return sorted

  const totals = new Map<string, number>()
  for (const id of sorted) {
    let total = 0
    for (const weight of weights.get(id)?.values() ?? []) total += weight
    totals.set(id, total)
  }

  const remaining = new Set(sorted)
  let current = sorted[0] as string
  for (const id of sorted) {
    const best = totals.get(current) ?? 0
    const candidate = totals.get(id) ?? 0
    if (candidate > best) current = id
  }

  const order: string[] = [current]
  remaining.delete(current)

  while (remaining.size > 0) {
    const neighbours = weights.get(current)
    let next: string | null = null
    let nextWeight = -1
    let nextTotal = -1

    for (const id of remaining) {
      const weight = neighbours?.get(id) ?? 0
      const total = totals.get(id) ?? 0

      if (
        weight > nextWeight ||
        (weight === nextWeight && total > nextTotal) ||
        (weight === nextWeight &&
          total === nextTotal &&
          next !== null &&
          id.localeCompare(next) < 0)
      ) {
        next = id
        nextWeight = weight
        nextTotal = total
      }
    }

    if (next === null) break
    order.push(next)
    remaining.delete(next)
    current = next
  }

  // Anything unreachable by the walk keeps a stable tail position.
  for (const id of sorted) if (remaining.has(id)) order.push(id)

  return order
}

/** Derives every lookup the explorer needs from one `/network/graph` payload. */
export function buildGraphIndex(graph: NetworkGraph): GraphIndex {
  const nodesById = new Map<string, NetworkNode>()
  for (const node of graph.nodes) nodesById.set(node.id, node)

  const edges = aggregateEdges(graph.edges).filter(
    (edge) => nodesById.has(edge.source) && nodesById.has(edge.target),
  )

  const edgesById = new Map<string, AggregatedEdge>()
  for (const edge of edges) edgesById.set(edge.id, edge)

  const edgesByNode = new Map<string, AggregatedEdge[]>()
  const neighborsById = new Map<string, Set<string>>()
  const relationshipCounts = new Map<string, number>()
  const personWeights = new Map<string, Map<string, number>>()

  const attach = (nodeId: string, edge: AggregatedEdge) => {
    const bucket = edgesByNode.get(nodeId)
    if (bucket) bucket.push(edge)
    else edgesByNode.set(nodeId, [edge])
  }

  const link = (a: string, b: string) => {
    const bucket = neighborsById.get(a)
    if (bucket) bucket.add(b)
    else neighborsById.set(a, new Set([b]))
  }

  const addWeight = (a: string, b: string, weight: number) => {
    const bucket = personWeights.get(a)
    if (bucket) bucket.set(b, (bucket.get(b) ?? 0) + weight)
    else personWeights.set(a, new Map([[b, weight]]))
  }

  for (const edge of edges) {
    attach(edge.source, edge)
    if (edge.target !== edge.source) attach(edge.target, edge)

    link(edge.source, edge.target)
    link(edge.target, edge.source)

    relationshipCounts.set(
      edge.relationship,
      (relationshipCounts.get(edge.relationship) ?? 0) + edge.count,
    )

    const source = nodesById.get(edge.source)
    const target = nodesById.get(edge.target)

    if (
      source?.entity_type === 'person' &&
      target?.entity_type === 'person' &&
      edge.source !== edge.target
    ) {
      addWeight(edge.source, edge.target, edge.count)
      addWeight(edge.target, edge.source, edge.count)
    }
  }

  const entityTypeCounts = Object.fromEntries(
    ENTITY_TYPES.map((type) => [type, 0]),
  ) as Record<EntityType, number>

  const personIds: string[] = []
  const satelliteIds: string[] = []

  for (const node of graph.nodes) {
    entityTypeCounts[node.entity_type] += 1
    if (node.entity_type === 'person') personIds.push(node.id)
    else satelliteIds.push(node.id)
  }

  const satellitesByOwner = new Map<string, string[]>()
  const unattachedNodes: string[] = []

  const typeRank = (id: string) => {
    const type = nodesById.get(id)?.entity_type
    const rank = type ? SATELLITE_TYPE_ORDER.indexOf(type) : -1
    return rank === -1 ? SATELLITE_TYPE_ORDER.length : rank
  }

  for (const id of satelliteIds) {
    // Vehicles, FIRs and surveillance events each hang off a person in the
    // backend graph. Pick the lowest person id so ownership is deterministic.
    let owner: string | null = null

    for (const neighbour of neighborsById.get(id) ?? []) {
      if (nodesById.get(neighbour)?.entity_type !== 'person') continue
      if (owner === null || neighbour.localeCompare(owner) < 0) owner = neighbour
    }

    if (owner === null) {
      unattachedNodes.push(id)
      continue
    }

    const bucket = satellitesByOwner.get(owner)
    if (bucket) bucket.push(id)
    else satellitesByOwner.set(owner, [id])
  }

  for (const bucket of satellitesByOwner.values()) {
    bucket.sort((a, b) => typeRank(a) - typeRank(b) || a.localeCompare(b))
  }

  unattachedNodes.sort((a, b) => typeRank(a) - typeRank(b) || a.localeCompare(b))

  return {
    nodes: graph.nodes,
    nodesById,
    edges,
    edgesById,
    edgesByNode,
    neighborsById,
    relationshipTypes: [...relationshipCounts.keys()].sort((a, b) =>
      a.localeCompare(b),
    ),
    relationshipCounts,
    entityTypeCounts,
    personOrder: seriatePeople(personIds, personWeights),
    satellitesByOwner,
    unattachedNodes,
  }
}

let memoisedIndex: { graph: NetworkGraph; index: GraphIndex } | null = null

/**
 * `buildGraphIndex` for callers that receive the same cached payload on every
 * mount, so navigating between person profiles does not re-index thousands of
 * edges. Holds a single entry, keyed by payload identity.
 */
export function getGraphIndex(graph: NetworkGraph): GraphIndex {
  if (memoisedIndex?.graph === graph) return memoisedIndex.index

  const index = buildGraphIndex(graph)
  memoisedIndex = { graph, index }
  return index
}

/* -------------------------------------------------------------------------- */
/* Layout                                                                      */
/* -------------------------------------------------------------------------- */

export const NODE_SIZE: Record<EntityType, { width: number; height: number }> =
  {
    person: { width: 166, height: 40 },
    vehicle: { width: 124, height: 30 },
    crime_event: { width: 124, height: 30 },
    surveillance_event: { width: 124, height: 30 },
  }

/** Icon hit-target only; the name sits beside the node, not inside a card. */
const COMPACT_NODE_SIZE: Record<EntityType, { width: number; height: number }> =
  {
    person: { width: 22, height: 22 },
    vehicle: { width: 20, height: 20 },
    crime_event: { width: 20, height: 20 },
    surveillance_event: { width: 20, height: 20 },
  }

const SELECTED_NODE_SIZE: Record<EntityType, { width: number; height: number }> =
  {
    person: { width: 28, height: 28 },
    vehicle: { width: 26, height: 26 },
    crime_event: { width: 26, height: 26 },
    surveillance_event: { width: 26, height: 26 },
  }

const OVERVIEW_IDEAL_DISTANCE = 340
const OVERVIEW_CUTOFF_FACTOR = 4.8
const OVERVIEW_SPRING_STRENGTH = 0.16
const OVERVIEW_MIN_GAP = 96
const OVERVIEW_ITERATIONS = 110
const CONNECTIVITY_CAP = 12
const LAYOUT_TARGET_WIDTH = 1680
const LAYOUT_TARGET_HEIGHT = 1120
const LAYOUT_PADDING = 140

export function nodeDegree(index: GraphIndex, nodeId: string): number {
  return index.neighborsById.get(nodeId)?.size ?? 0
}

/** Compact by default; the selected node is only slightly larger. */
export function nodeDisplaySize(
  entityType: EntityType,
  degree: number,
  options: { compact?: boolean; selected?: boolean } = {},
): { width: number; height: number } {
  if (options.selected) return SELECTED_NODE_SIZE[entityType]
  if (options.compact !== false) return COMPACT_NODE_SIZE[entityType]

  const base = NODE_SIZE[entityType]
  const t = Math.min(Math.max(degree, 0), CONNECTIVITY_CAP) / CONNECTIVITY_CAP
  const widthScale = entityType === 'person' ? 1 + t * 0.28 : 1 + t * 0.1
  const heightScale = entityType === 'person' ? 1 + t * 0.1 : 1
  return {
    width: Math.round(base.width * widthScale),
    height: Math.round(base.height * heightScale),
  }
}

interface ForcePoint {
  x: number
  y: number
}

const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5))

function seedOverviewPositions(
  index: GraphIndex,
  ids: string[],
  visible: ReadonlySet<string>,
  spacing: number,
): { positions: Map<string, ForcePoint>; anchors: Map<string, ForcePoint> } {
  const positions = new Map<string, ForcePoint>()
  const anchors = new Map<string, ForcePoint>()
  const people = index.personOrder.filter((id) => visible.has(id))

  people.forEach((personId, personIndex) => {
    const radius = spacing * Math.sqrt(personIndex + 0.65)
    const angle = personIndex * GOLDEN_ANGLE
    const point = {
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
    }
    positions.set(personId, { ...point })
    anchors.set(personId, { ...point })

    const owned = (index.satellitesByOwner.get(personId) ?? []).filter((id) =>
      visible.has(id),
    )
    owned.forEach((satelliteId, satelliteIndex) => {
      const orbit =
        angle +
        (satelliteIndex * 2 * Math.PI) / Math.max(owned.length, 1) +
        Math.PI / 5
      positions.set(satelliteId, {
        x: point.x + Math.cos(orbit) * (spacing * 0.38),
        y: point.y + Math.sin(orbit) * (spacing * 0.38),
      })
    })
  })

  const leftovers = ids.filter((id) => !positions.has(id))
  leftovers.forEach((id, leftoverIndex) => {
    const radius = spacing * Math.sqrt(people.length + leftoverIndex + 1.2)
    const angle = (people.length + leftoverIndex) * GOLDEN_ANGLE
    const point = {
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
    }
    positions.set(id, point)
    anchors.set(id, { ...point })
  })

  return { positions, anchors }
}

function pushDisplacement(
  dispX: Map<string, number>,
  dispY: Map<string, number>,
  id: string,
  dx: number,
  dy: number,
) {
  dispX.set(id, (dispX.get(id) ?? 0) + dx)
  dispY.set(id, (dispY.get(id) ?? 0) + dy)
}

function applyRepulsion(
  a: string,
  b: string,
  pa: ForcePoint,
  pb: ForcePoint,
  k: number,
  cutoff: number,
  minDistance: number,
  dispX: Map<string, number>,
  dispY: Map<string, number>,
) {
  let dx = pa.x - pb.x
  let dy = pa.y - pb.y
  let distance = Math.hypot(dx, dy)
  if (distance > cutoff) return
  if (distance < 0.01) {
    dx = 0.01
    dy = 0
    distance = 0.01
  }

  const overlap = Math.max(0, minDistance - distance)
  const force = ((k * k) / distance) * 1.85 + overlap * 1.45
  const fx = (dx / distance) * force
  const fy = (dy / distance) * force
  pushDisplacement(dispX, dispY, a, fx, fy)
  pushDisplacement(dispX, dispY, b, -fx, -fy)
}

function layoutNodeSize(
  index: GraphIndex,
  id: string,
  focusNodeId: string | null,
): { width: number; height: number } {
  const entityType = index.nodesById.get(id)?.entity_type ?? 'person'
  return nodeDisplaySize(entityType, nodeDegree(index, id), {
    compact: id !== focusNodeId,
    selected: id === focusNodeId,
  })
}

function visibleHopDistance(
  index: GraphIndex,
  originId: string,
  visible: ReadonlySet<string>,
): Map<string, number> {
  const distance = new Map<string, number>()
  if (!visible.has(originId)) return distance

  distance.set(originId, 0)
  const queue = [originId]
  for (let head = 0; head < queue.length; head += 1) {
    const current = queue[head]
    if (!current) continue
    const hop = distance.get(current) ?? 0
    for (const neighbour of index.neighborsById.get(current) ?? []) {
      if (!visible.has(neighbour) || distance.has(neighbour)) continue
      distance.set(neighbour, hop + 1)
      queue.push(neighbour)
    }
  }
  return distance
}

const TYPE_RING_ORDER: readonly EntityType[] = [
  'person',
  'vehicle',
  'crime_event',
  'surveillance_event',
]
const RING_SPLIT = 16

function ringRadius(count: number, inner: number): number {
  const needed = (Math.max(count, 1) * 84) / (2 * Math.PI)
  return Math.max(inner + 220, needed)
}

function placeOnRing(
  members: string[],
  radius: number,
  startAngle: number,
  positions: Map<string, ForcePoint>,
) {
  const step = (2 * Math.PI) / Math.max(members.length, 1)
  members.forEach((id, indexInRing) => {
    const angle = startAngle + indexInRing * step
    positions.set(id, {
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
    })
  })
}

function seedNeighborhoodPositions(
  index: GraphIndex,
  ids: string[],
  visible: ReadonlySet<string>,
  focusNodeId: string,
): Map<string, ForcePoint> {
  const positions = new Map<string, ForcePoint>()
  positions.set(focusNodeId, { x: 0, y: 0 })

  const hops = visibleHopDistance(index, focusNodeId, visible)
  const buckets = new Map<string, string[]>()
  const leftovers: string[] = []

  for (const id of ids) {
    if (id === focusNodeId) continue
    const hop = hops.get(id)
    if (hop === undefined) {
      leftovers.push(id)
      continue
    }
    const entityType = index.nodesById.get(id)?.entity_type ?? 'person'
    const key = `${hop}:${entityType}`
    const bucket = buckets.get(key)
    if (bucket) bucket.push(id)
    else buckets.set(key, [id])
  }

  for (const bucket of buckets.values()) {
    bucket.sort((a, b) => compareByDegreeThenId(index, a, b))
  }
  leftovers.sort((a, b) => compareByDegreeThenId(index, a, b))

  let previousRadius = 0
  const hopLevels = [...new Set(hops.values())]
    .filter((hop) => hop > 0)
    .sort((a, b) => a - b)

  for (const hop of hopLevels) {
    const hopAngle = -Math.PI / 2 + (hop - 1) * 0.28
    for (const entityType of TYPE_RING_ORDER) {
      const members = buckets.get(`${hop}:${entityType}`)
      if (!members || members.length === 0) continue

      if (members.length > RING_SPLIT) {
        const mid = Math.ceil(members.length / 2)
        const inner = members.slice(0, mid)
        const outer = members.slice(mid)
        const innerRadius = ringRadius(inner.length, previousRadius)
        placeOnRing(inner, innerRadius, hopAngle, positions)
        const outerRadius = ringRadius(outer.length, innerRadius)
        placeOnRing(outer, outerRadius, hopAngle + Math.PI / Math.max(outer.length, 2), positions)
        previousRadius = outerRadius
      } else {
        const radius = ringRadius(members.length, previousRadius)
        placeOnRing(members, radius, hopAngle, positions)
        previousRadius = radius
      }
    }
  }

  if (leftovers.length > 0) {
    const radius = ringRadius(leftovers.length, previousRadius)
    placeOnRing(leftovers, radius, -Math.PI / 2 + 0.4, positions)
  }

  return positions
}

function normalizeLayout(
  ids: string[],
  positions: Map<string, ForcePoint>,
  sizes: Map<string, { width: number; height: number }>,
  pinCenter: ForcePoint | null = null,
): Map<string, Point> {
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  for (const id of ids) {
    const point = positions.get(id)
    if (!point) continue
    minX = Math.min(minX, point.x)
    minY = Math.min(minY, point.y)
    maxX = Math.max(maxX, point.x)
    maxY = Math.max(maxY, point.y)
  }

  const spanX = Math.max(maxX - minX, 1)
  const spanY = Math.max(maxY - minY, 1)
  const usableWidth = LAYOUT_TARGET_WIDTH - LAYOUT_PADDING * 2
  const usableHeight = LAYOUT_TARGET_HEIGHT - LAYOUT_PADDING * 2
  const scale = Math.min(usableWidth / spanX, usableHeight / spanY)
  const centerX = pinCenter?.x ?? (minX + maxX) / 2
  const centerY = pinCenter?.y ?? (minY + maxY) / 2

  const layout = new Map<string, Point>()
  for (const id of ids) {
    const point = positions.get(id)
    const size = sizes.get(id) ?? COMPACT_NODE_SIZE.person
    if (!point) continue
    layout.set(id, {
      x: (point.x - centerX) * scale - size.width / 2,
      y: (point.y - centerY) * scale - size.height / 2,
    })
  }
  return layout
}

function runForcePass(
  ids: string[],
  positions: Map<string, ForcePoint>,
  sizes: Map<string, { width: number; height: number }>,
  springs: { source: string; target: string; rest: number; strength: number }[],
  {
    k,
    iterations,
    cutoff,
    gravity,
    minGap,
    pinId,
    anchors,
    anchorStrength = 0,
  }: {
    k: number
    iterations: number
    cutoff: number
    gravity: number
    minGap: number
    pinId?: string | null
    anchors?: Map<string, ForcePoint>
    anchorStrength?: number
  },
) {
  const n = ids.length
  const dispX = new Map<string, number>()
  const dispY = new Map<string, number>()

  for (let iter = 0; iter < iterations; iter += 1) {
    const temperature = k * 0.72 * (1 - iter / iterations)

    for (const id of ids) {
      dispX.set(id, 0)
      dispY.set(id, 0)
    }

    for (let i = 0; i < n; i += 1) {
      const a = ids[i]
      if (!a) continue
      const pa = positions.get(a)
      if (!pa) continue
      for (let j = i + 1; j < n; j += 1) {
        const b = ids[j]
        if (!b) continue
        const pb = positions.get(b)
        if (!pb) continue
        const minDistance =
          ((sizes.get(a)?.width ?? k) + (sizes.get(b)?.width ?? k)) / 2 + minGap
        applyRepulsion(a, b, pa, pb, k, cutoff, minDistance, dispX, dispY)
      }
    }

    for (const spring of springs) {
      const pa = positions.get(spring.source)
      const pb = positions.get(spring.target)
      if (!pa || !pb) continue
      let dx = pb.x - pa.x
      let dy = pb.y - pa.y
      let distance = Math.hypot(dx, dy)
      if (distance < 0.01) {
        dx = 0.01
        dy = 0
        distance = 0.01
      }
      const force = (spring.strength * (distance - spring.rest)) / distance
      pushDisplacement(dispX, dispY, spring.source, dx * force, dy * force)
      pushDisplacement(dispX, dispY, spring.target, -dx * force, -dy * force)
    }

    if (gravity !== 0) {
      for (const id of ids) {
        const point = positions.get(id)
        if (!point) continue
        pushDisplacement(dispX, dispY, id, -point.x * gravity, -point.y * gravity)
      }
    }

    if (anchors && anchorStrength !== 0) {
      for (const id of ids) {
        const point = positions.get(id)
        const anchor = anchors.get(id)
        if (!point || !anchor) continue
        pushDisplacement(
          dispX,
          dispY,
          id,
          (anchor.x - point.x) * anchorStrength,
          (anchor.y - point.y) * anchorStrength,
        )
      }
    }

    for (const id of ids) {
      if (id === pinId) continue
      const point = positions.get(id)
      if (!point) continue
      let dx = dispX.get(id) ?? 0
      let dy = dispY.get(id) ?? 0
      const magnitude = Math.hypot(dx, dy)
      if (magnitude > temperature && magnitude > 0) {
        dx = (dx / magnitude) * temperature
        dy = (dy / magnitude) * temperature
      }
      point.x += dx
      point.y += dy
    }

    if (pinId) {
      const pinned = positions.get(pinId)
      if (pinned) {
        pinned.x = 0
        pinned.y = 0
      }
    }
  }
}

/**
 * Overview: spread a small curated set across the canvas.
 * Neighborhood: keep the selected node in the centre with hop rings around it.
 */
export function computeLayout(
  index: GraphIndex,
  visible: ReadonlySet<string>,
  options: { focusNodeId?: string | null } = {},
): Map<string, Point> {
  const ids: string[] = []
  for (const node of index.nodes) {
    if (visible.has(node.id)) ids.push(node.id)
  }

  if (ids.length === 0) return new Map()

  const focusNodeId =
    options.focusNodeId && visible.has(options.focusNodeId)
      ? options.focusNodeId
      : null

  const sizes = new Map<string, { width: number; height: number }>()
  for (const id of ids) {
    sizes.set(id, layoutNodeSize(index, id, focusNodeId))
  }

  if (focusNodeId) {
    const positions = seedNeighborhoodPositions(index, ids, visible, focusNodeId)
    return normalizeLayout(ids, positions, sizes, { x: 0, y: 0 })
  }

  const k = OVERVIEW_IDEAL_DISTANCE
  const { positions, anchors } = seedOverviewPositions(index, ids, visible, k)
  const springs: { source: string; target: string; rest: number; strength: number }[] =
    []
  const seenPairs = new Set<string>()

  for (const edge of index.edges) {
    if (!visible.has(edge.source) || !visible.has(edge.target)) continue
    if (edge.source === edge.target) continue
    const key = pairKey(edge.source, edge.target)
    if (seenPairs.has(key)) continue
    seenPairs.add(key)

    const sourceType = index.nodesById.get(edge.source)?.entity_type
    const targetType = index.nodesById.get(edge.target)?.entity_type
    const satelliteLink =
      (sourceType === 'person') !== (targetType === 'person')
    if (!satelliteLink) continue

    springs.push({
      source: edge.source,
      target: edge.target,
      rest: k * 0.4,
      strength: OVERVIEW_SPRING_STRENGTH,
    })
  }

  runForcePass(ids, positions, sizes, springs, {
    k,
    iterations: OVERVIEW_ITERATIONS,
    cutoff: k * OVERVIEW_CUTOFF_FACTOR,
    gravity: 0,
    minGap: OVERVIEW_MIN_GAP,
    anchors,
    anchorStrength: 0.085,
  })

  return normalizeLayout(ids, positions, sizes)
}

/** Signed perpendicular offset that keeps parallel relationships apart. */
export function edgeCurveOffset(edge: AggregatedEdge): number {
  if (edge.parallelCount <= 1) return 0

  const centred = edge.parallelIndex - (edge.parallelCount - 1) / 2
  const direction = edge.source <= edge.target ? 1 : -1

  return centred * CURVE_STEP * direction
}

/* -------------------------------------------------------------------------- */
/* Filtering                                                                   */
/* -------------------------------------------------------------------------- */

export function computeVisibleNodeIds(
  index: GraphIndex,
  filters: GraphFilters,
  forced: Iterable<string> = [],
): Set<string> {
  const visible = new Set<string>()

  for (const node of index.nodes) {
    if (filters.entityTypes.has(node.entity_type)) visible.add(node.id)
  }

  // A traced path always stays on screen, otherwise tracing would silently do
  // nothing while a filter hides one of its hops.
  for (const id of forced) {
    if (index.nodesById.has(id)) visible.add(id)
  }

  return visible
}

export function computeVisibleEdges(
  index: GraphIndex,
  filters: GraphFilters,
  visibleNodeIds: ReadonlySet<string>,
  forcedEdgeIds: ReadonlySet<string> = new Set(),
): AggregatedEdge[] {
  return index.edges.filter((edge) => {
    if (!visibleNodeIds.has(edge.source)) return false
    if (!visibleNodeIds.has(edge.target)) return false
    return (
      filters.relationships.has(edge.relationship) || forcedEdgeIds.has(edge.id)
    )
  })
}

/* -------------------------------------------------------------------------- */
/* Progressive exploration                                                     */
/* -------------------------------------------------------------------------- */

export const OVERVIEW_NODE_TARGET = 40
const OVERVIEW_PERSON_TARGET = 28
const HOP_EXPANSION_CAPS = [48, 24, 16] as const
const MAX_NEIGHBORHOOD_NODES = 90
const OVERVIEW_LABEL_COUNT = 10

function compareByDegreeThenId(index: GraphIndex, a: string, b: string): number {
  const degreeDelta = nodeDegree(index, b) - nodeDegree(index, a)
  return degreeDelta !== 0 ? degreeDelta : a.localeCompare(b)
}

/** High-connectivity overview: about 30–50 nodes, never the full graph. */
export function selectOverviewNodeIds(
  index: GraphIndex,
  candidates: ReadonlySet<string>,
  target: number = OVERVIEW_NODE_TARGET,
): Set<string> {
  const people = index.personOrder
    .filter((id) => candidates.has(id))
    .sort((a, b) => compareByDegreeThenId(index, a, b))

  const selected = new Set<string>()
  for (const id of people) {
    if (selected.size >= OVERVIEW_PERSON_TARGET) break
    selected.add(id)
  }

  if (selected.size < OVERVIEW_PERSON_TARGET) {
    const extraPeople = [...candidates]
      .filter((id) => index.nodesById.get(id)?.entity_type === 'person')
      .sort((a, b) => compareByDegreeThenId(index, a, b))
    for (const id of extraPeople) {
      if (selected.size >= OVERVIEW_PERSON_TARGET) break
      selected.add(id)
    }
  }

  const satellites: string[] = []
  for (const personId of selected) {
    for (const satelliteId of index.satellitesByOwner.get(personId) ?? []) {
      if (candidates.has(satelliteId)) satellites.push(satelliteId)
    }
  }
  satellites.sort((a, b) => compareByDegreeThenId(index, a, b))
  for (const id of satellites) {
    if (selected.size >= target) break
    selected.add(id)
  }

  if (selected.size < Math.min(30, target)) {
    const remainder = [...candidates].sort((a, b) =>
      compareByDegreeThenId(index, a, b),
    )
    for (const id of remainder) {
      if (selected.size >= Math.min(30, target)) break
      selected.add(id)
    }
  }

  return selected
}

/** Selected node plus bounded n-hop neighbours that already pass filters. */
export function collectHopNeighborhood(
  index: GraphIndex,
  originId: string,
  hops: number,
  candidates: ReadonlySet<string>,
): Set<string> {
  const visible = new Set<string>()
  if (!index.nodesById.has(originId)) return visible
  visible.add(originId)

  let frontier = [originId]
  const depth = Math.max(1, Math.min(3, hops))

  for (let hop = 1; hop <= depth; hop += 1) {
    const discovered: string[] = []
    const seen = new Set<string>()
    for (const id of frontier) {
      for (const neighbour of index.neighborsById.get(id) ?? []) {
        if (visible.has(neighbour) || seen.has(neighbour)) continue
        if (!candidates.has(neighbour) && neighbour !== originId) continue
        seen.add(neighbour)
        discovered.push(neighbour)
      }
    }

    discovered.sort((a, b) => compareByDegreeThenId(index, a, b))
    const remaining = MAX_NEIGHBORHOOD_NODES - visible.size
    const cap = Math.min(HOP_EXPANSION_CAPS[hop - 1] ?? 16, remaining)
    if (cap <= 0) break
    const next: string[] = []
    for (const id of discovered.slice(0, cap)) {
      visible.add(id)
      next.push(id)
    }
    frontier = next
    if (frontier.length === 0) break
  }

  return visible
}

export function computeExplorationNodeIds(
  index: GraphIndex,
  {
    filteredIds,
    selectedNodeId,
    hopDepth,
    pathNodeIds,
    communityMembers,
  }: {
    filteredIds: ReadonlySet<string>
    selectedNodeId: string | null
    hopDepth: 1 | 2 | 3
    pathNodeIds: readonly string[]
    communityMembers: ReadonlySet<string>
  },
): Set<string> {
  let visible: Set<string>

  if (selectedNodeId && index.nodesById.has(selectedNodeId)) {
    visible = collectHopNeighborhood(
      index,
      selectedNodeId,
      hopDepth,
      filteredIds,
    )
  } else if (communityMembers.size > 0) {
    const members = new Set<string>()
    for (const id of communityMembers) {
      if (filteredIds.has(id)) members.add(id)
    }
    visible =
      members.size > OVERVIEW_NODE_TARGET + 10
        ? selectOverviewNodeIds(index, members)
        : members
  } else {
    visible = selectOverviewNodeIds(index, filteredIds)
  }

  for (const id of pathNodeIds) {
    if (index.nodesById.has(id)) visible.add(id)
  }
  if (selectedNodeId && index.nodesById.has(selectedNodeId)) {
    visible.add(selectedNodeId)
  }

  return visible
}

function importantOverviewLabelIds(
  index: GraphIndex,
  visibleNodeIds: ReadonlySet<string>,
): Set<string> {
  return new Set(
    [...visibleNodeIds]
      .filter((id) => index.nodesById.get(id)?.entity_type === 'person')
      .sort((a, b) => compareByDegreeThenId(index, a, b))
      .slice(0, OVERVIEW_LABEL_COUNT),
  )
}

/* -------------------------------------------------------------------------- */
/* View assembly                                                               */
/* -------------------------------------------------------------------------- */

export interface BuildGraphViewInput {
  index: GraphIndex
  visibleNodeIds: ReadonlySet<string>
  visibleEdges: AggregatedEdge[]
  positions: ReadonlyMap<string, Point>
  selection: GraphSelection | null
  communityMembers: ReadonlySet<string>
  path: ActivePath | null
  exploreFocusId?: string | null
  explorationHops?: 1 | 2 | 3
}

/**
 * Decides what each visible element looks like.
 *
 * Emphasis precedence: an active path wins, then a highlighted community, then
 * the current selection. Relationship labels are limited to path hops and the
 * selected edge so the canvas never fills with text.
 */
export function buildGraphView({
  index,
  visibleNodeIds,
  visibleEdges,
  positions,
  selection,
  communityMembers,
  path,
  exploreFocusId = null,
  explorationHops = 1,
}: BuildGraphViewInput): GraphView {
  const pathRoles = new Map<string, PathRole>()

  if (path) {
    path.nodeIds.forEach((id, position) => {
      pathRoles.set(
        id,
        position === 0
          ? 'source'
          : position === path.nodeIds.length - 1
            ? 'target'
            : 'step',
      )
    })
  }

  const pathActive = pathRoles.size > 0
  const communityActive = communityMembers.size > 0

  const selectedNodeId = selection?.kind === 'node' ? selection.id : null
  const selectedEdgeId = selection?.kind === 'edge' ? selection.id : null
  const focusNodeId = selectedNodeId ?? exploreFocusId

  const incidentEdgeIds = new Set<string>()
  const neighborhoodIds = new Set<string>()
  if (focusNodeId !== null) {
    neighborhoodIds.add(focusNodeId)
    for (const neighbour of index.neighborsById.get(focusNodeId) ?? []) {
      neighborhoodIds.add(neighbour)
    }
    for (const edge of index.edgesByNode.get(focusNodeId) ?? []) {
      incidentEdgeIds.add(edge.id)
    }
  }
  const neighborhoodActive = neighborhoodIds.size > 0
  const overviewLabelIds = focusNodeId
    ? new Set<string>()
    : importantOverviewLabelIds(index, visibleNodeIds)

  const nodes: GraphViewNode[] = []

  for (const entity of index.nodes) {
    if (!visibleNodeIds.has(entity.id)) continue

    const position = positions.get(entity.id)
    if (!position) continue

    const pathRole = pathRoles.get(entity.id) ?? null
    const inCommunity = communityMembers.has(entity.id)
    const inNeighborhood =
      neighborhoodActive && neighborhoodIds.has(entity.id)
    const selected = entity.id === selectedNodeId
    const labelPriority: GraphViewNode['labelPriority'] =
      selected ||
      pathRole === 'source' ||
      pathRole === 'target' ||
      inNeighborhood ||
      overviewLabelIds.has(entity.id)
        ? 'always'
        : pathRole !== null
          ? 'zoom'
          : 'hidden'

    nodes.push({
      id: entity.id,
      entity,
      position,
      primary: entityPrimaryLabel(entity),
      secondary: entitySecondaryLabel(entity),
      selected,
      dimmed: pathActive
        ? pathRole === null
        : communityActive
          ? !inCommunity
          : neighborhoodActive && explorationHops > 1
            ? !selected && !inNeighborhood
            : false,
      pathRole,
      inCommunity: communityActive && inCommunity,
      inNeighborhood: inNeighborhood && !selected,
      labelPriority,
      size: nodeDisplaySize(entity.entity_type, nodeDegree(index, entity.id), {
        compact: !selected,
        selected,
      }),
    })
  }

  const edges: GraphViewEdge[] = visibleEdges.map((edge) => {
    const inPath = path?.edgeIds.has(edge.id) ?? false
    const isSelectedEdge = edge.id === selectedEdgeId

    let emphasis: EdgeEmphasis = 'normal'

    if (pathActive) {
      emphasis = inPath ? 'active' : 'dimmed'
    } else if (communityActive) {
      emphasis =
        communityMembers.has(edge.source) && communityMembers.has(edge.target)
          ? 'normal'
          : 'dimmed'
    } else if (neighborhoodActive) {
      const innerLink =
        neighborhoodIds.has(edge.source) && neighborhoodIds.has(edge.target)
      if (isSelectedEdge || incidentEdgeIds.has(edge.id)) {
        emphasis = 'active'
      } else if (explorationHops > 1 && !innerLink) {
        emphasis = 'dimmed'
      } else {
        emphasis = 'normal'
      }
    } else if (isSelectedEdge) {
      emphasis = 'active'
    }

    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      relationship: edge.relationship,
      count: edge.count,
      curveOffset: edgeCurveOffset(edge),
      emphasis,
      showLabel: inPath || isSelectedEdge,
    }
  })

  return { nodes, edges }
}

/* -------------------------------------------------------------------------- */
/* Search                                                                      */
/* -------------------------------------------------------------------------- */

export function buildEntityOptions(nodes: NetworkNode[]): EntityOption[] {
  return nodes
    .map((node) => ({
      id: node.id,
      label: entityPrimaryLabel(node),
      detail: entitySecondaryLabel(node) ?? node.id,
      entityType: node.entity_type,
    }))
    .sort(
      (a, b) => a.label.localeCompare(b.label) || a.id.localeCompare(b.id),
    )
}

/** Case-insensitive match on the visible identifiers of an entity. */
export function searchEntityOptions(
  options: EntityOption[],
  query: string,
  limit = 30,
): EntityOption[] {
  const needle = query.trim().toLowerCase()
  if (needle === '') return options.slice(0, limit)

  const starts: EntityOption[] = []
  const contains: EntityOption[] = []

  for (const option of options) {
    const id = option.id.toLowerCase()
    const label = option.label.toLowerCase()
    const detail = option.detail.toLowerCase()

    if (id.startsWith(needle) || label.startsWith(needle)) {
      starts.push(option)
    } else if (
      id.includes(needle) ||
      label.includes(needle) ||
      detail.includes(needle)
    ) {
      contains.push(option)
    }

    if (starts.length >= limit) break
  }

  return [...starts, ...contains].slice(0, limit)
}

/* -------------------------------------------------------------------------- */
/* Relationship summaries                                                      */
/* -------------------------------------------------------------------------- */

export interface RelationshipSummary {
  relationship: string
  /** Distinct aggregated links carrying this relationship. */
  links: number
  /** Underlying API records. */
  interactions: number
}

export function summariseNodeRelationships(
  index: GraphIndex,
  nodeId: string,
): RelationshipSummary[] {
  const totals = new Map<string, RelationshipSummary>()

  for (const edge of index.edgesByNode.get(nodeId) ?? []) {
    const existing = totals.get(edge.relationship)

    if (existing) {
      existing.links += 1
      existing.interactions += edge.count
    } else {
      totals.set(edge.relationship, {
        relationship: edge.relationship,
        links: 1,
        interactions: edge.count,
      })
    }
  }

  return [...totals.values()].sort(
    (a, b) =>
      b.interactions - a.interactions ||
      a.relationship.localeCompare(b.relationship),
  )
}

export interface EdgeMetadataSummary {
  totalAmount: number | null
  totalDurationSeconds: number | null
  earliest: string | null
  latest: string | null
  callTypes: { value: string; count: number }[]
}

/** Aggregates only what the underlying records actually carry. */
export function summariseEdgeRecords(
  edge: AggregatedEdge,
): EdgeMetadataSummary {
  let totalAmount: number | null = null
  let totalDurationSeconds: number | null = null
  let earliest: string | null = null
  let latest: string | null = null
  const callTypes = new Map<string, number>()

  for (const record of edge.records) {
    if (typeof record.amount === 'number' && Number.isFinite(record.amount)) {
      totalAmount = (totalAmount ?? 0) + record.amount
    }

    if (
      typeof record.duration === 'number' &&
      Number.isFinite(record.duration)
    ) {
      totalDurationSeconds = (totalDurationSeconds ?? 0) + record.duration
    }

    const callType = cleanValue(record.call_type)
    if (callType) callTypes.set(callType, (callTypes.get(callType) ?? 0) + 1)

    const stamp = cleanValue(record.timestamp) ?? cleanValue(record.date)
    if (stamp) {
      if (earliest === null || stamp < earliest) earliest = stamp
      if (latest === null || stamp > latest) latest = stamp
    }
  }

  return {
    totalAmount,
    totalDurationSeconds,
    earliest,
    latest,
    callTypes: [...callTypes.entries()]
      .map(([value, count]) => ({ value, count }))
      .sort((a, b) => b.count - a.count || a.value.localeCompare(b.value)),
  }
}

/* -------------------------------------------------------------------------- */
/* Path resolution                                                             */
/* -------------------------------------------------------------------------- */

/**
 * Maps a `/analytics/connection` response onto the aggregated edges on screen.
 *
 * The backend reports one relationship per hop even when several exist between
 * the pair, so any aggregated edge joining the hop is treated as part of the
 * path when the reported relationship cannot be matched exactly.
 */
export function resolveActivePath(
  result: ConnectionFound,
  index: GraphIndex,
): ActivePath {
  const nodeIds = result.nodes.map((node) => node.entity_id)
  const edgeIds = new Set<string>()

  const hops = result.relationships.map((hop) => {
    const exactId =
      hop.relationship === null
        ? null
        : `${hop.source}|${hop.relationship}|${hop.target}`

    if (exactId !== null && index.edgesById.has(exactId)) {
      edgeIds.add(exactId)
    } else {
      for (const edge of index.edges) {
        const forward = edge.source === hop.source && edge.target === hop.target
        const backward =
          edge.source === hop.target && edge.target === hop.source
        if (forward || backward) edgeIds.add(edge.id)
      }
    }

    return {
      from: hop.source,
      to: hop.target,
      relationship: hop.relationship,
    }
  })

  return {
    sourceId: result.source,
    targetId: result.target,
    degrees: result.degrees_of_separation,
    nodeIds,
    hops,
    edgeIds,
  }
}
