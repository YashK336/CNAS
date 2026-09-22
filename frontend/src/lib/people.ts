/**
 * Pure derivations behind the People module.
 *
 * Every value returned here traces back to a field the FastAPI backend
 * actually returned: `/entities/persons` for identity, `/analytics/centrality`
 * for network metrics, `/analytics/risk` for risk, and `/network/graph` for
 * relationships. Nothing is inferred, estimated or invented.
 */

import {
  NODE_SIZE,
  cleanValue,
  edgeCurveOffset,
  entityPrimaryLabel,
  entitySecondaryLabel,
  summariseEdgeRecords,
} from '@/lib/graph'
import type {
  AggregatedEdge,
  AnomalyProfile,
  CentralityResult,
  ConnectedPerson,
  EntityType,
  GraphIndex,
  GraphViewEdge,
  GraphViewNode,
  NetworkNode,
  Person,
  PersonActivityEvent,
  PersonAssociations,
  PersonGraphContext,
  PersonNeighbourhood,
  PersonNode,
  PersonProfile,
  PersonRelationship,
  PersonRosterRow,
  PeopleSort,
  PeopleSortKey,
  RelationshipCount,
  RiskProfile,
} from '@/types'

/* -------------------------------------------------------------------------- */
/* Roster                                                                      */
/* -------------------------------------------------------------------------- */

/**
 * Joins the three roster endpoints on the person id.
 *
 * `/entities/persons` is the spine: centrality and risk are keyed by
 * `entity_id` and are simply absent for anyone the corresponding analysis did
 * not cover, which surfaces as `null` rather than a placeholder number.
 */
export function buildRosterRows(
  persons: Person[],
  centrality: CentralityResult[] | null,
  riskProfiles: RiskProfile[] | null,
): PersonRosterRow[] {
  const centralityById = new Map<string, CentralityResult>()
  for (const entry of centrality ?? []) {
    centralityById.set(String(entry.entity_id), entry)
  }

  const riskById = new Map<string, RiskProfile>()
  for (const entry of riskProfiles ?? []) {
    riskById.set(String(entry.entity_id), entry)
  }

  return persons.map((person) => {
    const personId = String(person.person_id)
    const metrics = centralityById.get(personId)
    const risk = riskById.get(personId)

    const haystack = [
      person.name,
      personId,
      person.phone,
      person.vehicle_no,
      person.bank_account,
      person.home_city,
    ]
      .map((value) => cleanValue(value))
      .filter((value): value is string => value !== null)
      .join(' ')
      .toLowerCase()

    return {
      person,
      riskScore: risk ? risk.risk_score : null,
      riskLevel: risk ? risk.risk_level : null,
      pagerank: metrics ? metrics.pagerank : null,
      betweenness: metrics ? metrics.betweenness_centrality : null,
      haystack,
    }
  })
}

/** Case-insensitive substring match across every identifier in the row. */
export function filterRosterRows(
  rows: PersonRosterRow[],
  query: string,
): PersonRosterRow[] {
  const needle = query.trim().toLowerCase()
  if (needle === '') return rows

  return rows.filter((row) => row.haystack.includes(needle))
}

function sortValue(
  row: PersonRosterRow,
  key: PeopleSortKey,
): string | number | null {
  switch (key) {
    case 'name':
      return cleanValue(row.person.name)
    case 'person_id':
      return cleanValue(row.person.person_id)
    case 'city':
      return cleanValue(row.person.home_city)
    case 'risk':
      return row.riskScore
    case 'pagerank':
      return row.pagerank
    case 'betweenness':
      return row.betweenness
  }
}

/**
 * Sorts a copy. Rows missing the sorted value always land at the bottom,
 * whichever direction is active, and ties fall back to the person id so the
 * order never depends on the incoming array.
 */
export function sortRosterRows(
  rows: PersonRosterRow[],
  sort: PeopleSort,
): PersonRosterRow[] {
  const factor = sort.direction === 'asc' ? 1 : -1

  return [...rows].sort((a, b) => {
    const left = sortValue(a, sort.key)
    const right = sortValue(b, sort.key)

    if (left === null || right === null) {
      if (left !== right) return left === null ? 1 : -1
    } else {
      const compared =
        typeof left === 'string' && typeof right === 'string'
          ? left.localeCompare(right)
          : Number(left) - Number(right)

      if (compared !== 0) return compared * factor
    }

    return String(a.person.person_id).localeCompare(String(b.person.person_id))
  })
}

/* -------------------------------------------------------------------------- */
/* Relationship derivation                                                     */
/* -------------------------------------------------------------------------- */

export function isSocialRelationship(relationship: string): boolean {
  return relationship.startsWith('SOCIAL_')
}

/**
 * Every aggregated link touching the person, as seen from the person.
 *
 * `GraphIndex` already collapses the MultiDiGraph into one entry per
 * `(source, relationship, target)` while keeping the raw records, so both
 * directions of the same relationship stay separate and countable.
 */
function personRelationships(
  index: GraphIndex,
  personId: string,
): PersonRelationship[] {
  const links: PersonRelationship[] = []

  for (const edge of index.edgesByNode.get(personId) ?? []) {
    const outgoing = edge.source === personId
    const counterpartId = outgoing ? edge.target : edge.source
    if (counterpartId === personId) continue

    const counterpart = index.nodesById.get(counterpartId) ?? null
    const metadata = summariseEdgeRecords(edge)

    links.push({
      id: edge.id,
      relationship: edge.relationship,
      outgoing,
      counterpartId,
      counterpart,
      counterpartLabel: counterpart
        ? entityPrimaryLabel(counterpart)
        : counterpartId,
      counterpartDetail: counterpart ? entitySecondaryLabel(counterpart) : null,
      count: edge.count,
      records: edge.records,
      totalAmount: metadata.totalAmount,
      totalDurationSeconds: metadata.totalDurationSeconds,
      earliest: metadata.earliest,
      latest: metadata.latest,
    })
  }

  return links
}

/** Backend date carried by an event node, used where the edge has none. */
function eventNodeDate(node: NetworkNode | null): string | null {
  if (!node) return null
  if (node.entity_type === 'crime_event') return cleanValue(node.date)
  if (node.entity_type === 'surveillance_event') return cleanValue(node.timestamp)
  return null
}

function byNewestEvent(a: PersonRelationship, b: PersonRelationship): number {
  const left = eventNodeDate(a.counterpart)
  const right = eventNodeDate(b.counterpart)
  if (left !== right) {
    if (left === null) return 1
    if (right === null) return -1
    return right.localeCompare(left)
  }
  return a.counterpartId.localeCompare(b.counterpartId)
}

function byActivity(a: PersonRelationship, b: PersonRelationship): number {
  if (a.count !== b.count) return b.count - a.count
  if (a.latest !== b.latest) {
    if (a.latest === null) return 1
    if (b.latest === null) return -1
    return b.latest.localeCompare(a.latest)
  }
  return a.counterpartId.localeCompare(b.counterpartId)
}

function byCounterpartId(
  a: PersonRelationship,
  b: PersonRelationship,
): number {
  return a.counterpartId.localeCompare(b.counterpartId)
}

function groupAssociations(
  links: PersonRelationship[],
  personId: string,
): PersonAssociations {
  const counterpartType = (link: PersonRelationship): EntityType | null =>
    link.counterpart?.entity_type ?? null

  return {
    vehicles: links
      .filter((link) => counterpartType(link) === 'vehicle')
      .sort(byCounterpartId),
    crimeEvents: links
      .filter((link) => counterpartType(link) === 'crime_event')
      .sort(byNewestEvent),
    surveillance: links
      .filter((link) => counterpartType(link) === 'surveillance_event')
      .sort(byNewestEvent),
    connectedPeople: connectedPeople(links, personId),
    financial: links
      .filter((link) => link.relationship === 'TRANSFERRED_MONEY')
      .sort(byActivity),
    calls: links
      .filter((link) => link.relationship === 'CALLED')
      .sort(byActivity),
    social: links
      .filter((link) => isSocialRelationship(link.relationship))
      .sort(byActivity),
  }
}

/** Collapses person-to-person links into one entry per neighbouring person. */
function connectedPeople(
  links: PersonRelationship[],
  personId: string,
): ConnectedPerson[] {
  const byPerson = new Map<
    string,
    { entry: ConnectedPerson; relationships: Set<string> }
  >()

  for (const link of links) {
    if (link.counterpart?.entity_type !== 'person') continue
    if (link.counterpartId === personId) continue

    const node = link.counterpart
    const existing = byPerson.get(link.counterpartId)

    if (existing) {
      existing.entry.interactions += link.count
      existing.relationships.add(link.relationship)
      continue
    }

    byPerson.set(link.counterpartId, {
      entry: {
        entityId: link.counterpartId,
        name: cleanValue(node.name) ?? link.counterpartId,
        homeCity: cleanValue(node.home_city),
        riskGroup: cleanValue(node.risk_group),
        interactions: link.count,
        relationships: [],
      },
      relationships: new Set([link.relationship]),
    })
  }

  return [...byPerson.values()]
    .map(({ entry, relationships }) => ({
      ...entry,
      relationships: [...relationships].sort((a, b) => a.localeCompare(b)),
    }))
    .sort(
      (a, b) =>
        b.interactions - a.interactions ||
        a.name.localeCompare(b.name) ||
        a.entityId.localeCompare(b.entityId),
    )
}

/** Connection summary: API records and distinct counterparts per relationship. */
function summariseRelationshipCounts(
  links: PersonRelationship[],
): RelationshipCount[] {
  const totals = new Map<
    string,
    { interactions: number; counterparts: Set<string> }
  >()

  for (const link of links) {
    const existing = totals.get(link.relationship)

    if (existing) {
      existing.interactions += link.count
      existing.counterparts.add(link.counterpartId)
      continue
    }

    totals.set(link.relationship, {
      interactions: link.count,
      counterparts: new Set([link.counterpartId]),
    })
  }

  return [...totals.entries()]
    .map(([relationship, value]) => ({
      relationship,
      interactions: value.interactions,
      counterparts: value.counterparts.size,
    }))
    .sort(
      (a, b) =>
        b.interactions - a.interactions ||
        a.relationship.localeCompare(b.relationship),
    )
}

/**
 * Dated relationship records, newest first.
 *
 * `CALLED`, `TRANSFERRED_MONEY` and `SOCIAL_*` edges carry their own date.
 * `INVOLVED_IN` and `OBSERVED_AT` do not, so the date is read from the linked
 * FIR / surveillance node and flagged as such. `OWNS` has no date anywhere and
 * is therefore absent from the timeline rather than given one.
 */
function buildActivity(links: PersonRelationship[]): PersonActivityEvent[] {
  const events: PersonActivityEvent[] = []

  for (const link of links) {
    const nodeDate = eventNodeDate(link.counterpart)

    link.records.forEach((record, position) => {
      const recordDate = cleanValue(record.timestamp) ?? cleanValue(record.date)
      const at = recordDate ?? nodeDate
      if (at === null) return

      events.push({
        id: `${link.id}#${position}`,
        at,
        relationship: link.relationship,
        outgoing: link.outgoing,
        counterpartId: link.counterpartId,
        counterpartLabel: link.counterpartLabel,
        amount:
          typeof record.amount === 'number' && Number.isFinite(record.amount)
            ? record.amount
            : null,
        durationSeconds:
          typeof record.duration === 'number' &&
          Number.isFinite(record.duration)
            ? record.duration
            : null,
        callType: cleanValue(record.call_type),
        fromEventNode: recordDate === null,
      })
    })
  }

  return events.sort(
    (a, b) => b.at.localeCompare(a.at) || a.id.localeCompare(b.id),
  )
}

/* -------------------------------------------------------------------------- */
/* Mini network                                                                */
/* -------------------------------------------------------------------------- */

/**
 * Neighbours drawn in the profile's local graph.
 *
 * Kept small on purpose: this is a context view, and a readable node label at
 * this panel size is worth more than completeness. The exact figure is shown
 * next to the canvas, and Network Explorer holds the full neighbourhood.
 */
export const NEIGHBOURHOOD_LIMIT = 12

/** Vertical radius grows with the neighbour count; the ring is a wide ellipse
    because the panel is far wider than it is tall. */
const RING_PITCH = 13
const RING_MIN_RADIUS_Y = 150
const RING_ASPECT = 2.2
/** Alternating radii give each node and its label extra arc clearance. */
const RING_OUTER_FACTOR = 1.1
const LABEL_EDGE_LIMIT = 22

const TYPE_RANK: Record<EntityType, number> = {
  person: 0,
  vehicle: 1,
  crime_event: 2,
  surveillance_event: 3,
}

function viewNode(
  entity: NetworkNode,
  centerX: number,
  centerY: number,
  selected: boolean,
): GraphViewNode {
  const size = NODE_SIZE[entity.entity_type]

  return {
    id: entity.id,
    entity,
    position: {
      x: centerX - size.width / 2,
      y: centerY - size.height / 2,
    },
    primary: entityPrimaryLabel(entity),
    secondary: entitySecondaryLabel(entity),
    selected,
    dimmed: false,
    pathRole: null,
    inCommunity: false,
    inNeighborhood: false,
    labelPriority: selected ? 'always' : 'zoom',
    size,
  }
}

/**
 * The person's immediate neighbourhood as a star: the person at the centre,
 * their strongest direct links around them. Only edges incident to the person
 * are drawn — this is a local context view, not a second graph explorer.
 */
export function buildNeighbourhood(
  index: GraphIndex,
  personId: string,
  limit: number = NEIGHBOURHOOD_LIMIT,
): PersonNeighbourhood {
  const center = index.nodesById.get(personId)
  const empty: PersonNeighbourhood = {
    view: { nodes: [], edges: [] },
    edges: [],
    shown: 0,
    total: 0,
  }

  if (!center) return empty

  const incident = index.edgesByNode.get(personId) ?? []

  const weights = new Map<string, number>()
  for (const edge of incident) {
    const other = edge.source === personId ? edge.target : edge.source
    if (other === personId) continue
    if (!index.nodesById.has(other)) continue
    weights.set(other, (weights.get(other) ?? 0) + edge.count)
  }

  const rank = (id: string) => {
    const type = index.nodesById.get(id)?.entity_type
    return type ? TYPE_RANK[type] : TYPE_RANK.surveillance_event + 1
  }

  const neighbours = [...weights.keys()]
    // Keep the strongest links when capping…
    .sort(
      (a, b) =>
        (weights.get(b) ?? 0) - (weights.get(a) ?? 0) ||
        rank(a) - rank(b) ||
        a.localeCompare(b),
    )
    .slice(0, limit)
    // …then place them grouped by entity type so the ring reads cleanly.
    .sort((a, b) => rank(a) - rank(b) || a.localeCompare(b))

  if (neighbours.length === 0) {
    return {
      view: { nodes: [viewNode(center, 0, 0, true)], edges: [] },
      edges: [],
      shown: 0,
      total: 0,
    }
  }

  const radiusY = Math.max(
    RING_MIN_RADIUS_Y,
    neighbours.length * RING_PITCH,
  )
  const radiusX = radiusY * RING_ASPECT

  const nodes: GraphViewNode[] = [viewNode(center, 0, 0, true)]

  neighbours.forEach((id, position) => {
    const entity = index.nodesById.get(id)
    if (!entity) return

    const angle = -Math.PI / 2 + (position * 2 * Math.PI) / neighbours.length
    const spread = position % 2 === 0 ? 1 : RING_OUTER_FACTOR

    nodes.push(
      viewNode(
        entity,
        Math.cos(angle) * radiusX * spread,
        Math.sin(angle) * radiusY * spread,
        false,
      ),
    )
  })

  const shownIds = new Set(neighbours)
  const edges: AggregatedEdge[] = incident.filter((edge) => {
    const other = edge.source === personId ? edge.target : edge.source
    return other !== personId && shownIds.has(other)
  })

  /*
   * A hub can share half a dozen relationship types with one neighbour, so
   * labelling every spoke buries the canvas. Label the heaviest spoke per
   * neighbour instead: the text still describes exactly the edge it sits on,
   * and the full breakdown lives in the association and summary panels.
   */
  const labelled = new Set<string>()
  if (edges.length > 0) {
    const strongest = new Map<string, AggregatedEdge>()

    for (const edge of edges) {
      const other = edge.source === personId ? edge.target : edge.source
      const current = strongest.get(other)

      if (
        !current ||
        edge.count > current.count ||
        (edge.count === current.count &&
          edge.relationship.localeCompare(current.relationship) < 0)
      ) {
        strongest.set(other, edge)
      }
    }

    if (strongest.size <= LABEL_EDGE_LIMIT) {
      for (const edge of strongest.values()) labelled.add(edge.id)
    }
  }

  const viewEdges: GraphViewEdge[] = edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    relationship: edge.relationship,
    count: edge.count,
    curveOffset: edgeCurveOffset(edge),
    emphasis: 'normal',
    showLabel: labelled.has(edge.id),
  }))

  return {
    view: { nodes, edges: viewEdges },
    edges,
    shown: neighbours.length,
    total: weights.size,
  }
}

/* -------------------------------------------------------------------------- */
/* Profile assembly                                                            */
/* -------------------------------------------------------------------------- */

export interface BuildPersonProfileInput {
  personId: string
  person: Person
  risk: RiskProfile | null
  anomaly: AnomalyProfile | null
  centrality: CentralityResult | null
  /** Null while `/network/graph` is loading or after it failed. */
  index: GraphIndex | null
}

/** Graph-derived half of the profile; separate so it can load independently. */
export function buildPersonGraphContext(
  index: GraphIndex,
  personId: string,
): PersonGraphContext {
  const node = index.nodesById.get(personId) ?? null
  const links = personRelationships(index, personId)

  return {
    node: node?.entity_type === 'person' ? (node as PersonNode) : null,
    directConnections: index.neighborsById.get(personId)?.size ?? 0,
    relationshipCounts: summariseRelationshipCounts(links),
    associations: groupAssociations(links, personId),
    activity: buildActivity(links),
    neighbourhood: buildNeighbourhood(index, personId),
  }
}

export function buildPersonProfile({
  personId,
  person,
  risk,
  anomaly,
  centrality,
  index,
}: BuildPersonProfileInput): PersonProfile {
  return {
    personId,
    person,
    risk,
    anomaly,
    centrality,
    graph: index ? buildPersonGraphContext(index, personId) : null,
  }
}
