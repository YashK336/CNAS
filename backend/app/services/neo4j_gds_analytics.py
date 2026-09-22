"""Neo4j GDS graph projections and Person-level analytics for CNAS."""

from __future__ import annotations

import threading
from typing import Any

from app.core.config import gds_session_settings
from app.services.neo4j_analytics import Neo4jUnavailableError, run_cypher

GRAPH_PROJECTION_NAME = "cnas-person-analytics"
TEMPORAL_GRAPH_PROJECTION_NAME = f"{GRAPH_PROJECTION_NAME}-temporal"
CNAS_GRAPH_PROJECTION_NAMES = (
    GRAPH_PROJECTION_NAME,
    TEMPORAL_GRAPH_PROJECTION_NAME,
)

PERSON_RELATIONSHIP_PROJECTION = {
    "CALLED": {"orientation": "UNDIRECTED"},
    "TRANSFERRED_MONEY_TO": {"orientation": "UNDIRECTED"},
    "SOCIAL_REPLY": {"orientation": "UNDIRECTED"},
    "SOCIAL_RETWEET": {"orientation": "UNDIRECTED"},
    "SOCIAL_MENTION": {"orientation": "UNDIRECTED"},
}

PERSON_RELATIONSHIP_TYPES = tuple(PERSON_RELATIONSHIP_PROJECTION.keys())

TEMPORAL_RELATIONSHIP_FILTER = """
(
  $from_datetime IS NULL
  OR coalesce(r.timestamp, r.date) IS NULL
  OR coalesce(r.timestamp, r.date) >= $from_datetime
)
AND (
  $to_datetime IS NULL
  OR coalesce(r.timestamp, r.date) IS NULL
  OR coalesce(r.timestamp, r.date) <= $to_datetime
)
"""

GRAPH_EXISTS_CYPHER = """
CALL gds.graph.exists($graph_name) YIELD exists
RETURN exists
"""

DROP_GRAPH_CYPHER = """
CALL gds.graph.drop($graph_name, false) YIELD graphName
RETURN graphName
"""

_projection_lock = threading.Lock()

SESSION_GET_OR_CREATE_CYPHER = """
CALL gds.session.getOrCreate(
  $session_name,
  $memory,
  duration({minutes: $ttl_minutes})
)
YIELD id, name, memory, status
RETURN id, name, memory, status
"""

PROJECT_GRAPH_CYPHER = """
CALL gds.graph.project(
  $graph_name,
  'Person',
  $relationship_types,
  {
    sessionId: $session_id,
    undirectedRelationshipTypes: $relationship_types
  }
)
YIELD graphName, nodeCount, relationshipCount, projectMillis
RETURN graphName, nodeCount, relationshipCount, projectMillis
"""

PROJECT_GRAPH_CYPHER_TEMPORAL = f"""
CYPHER runtime=parallel
MATCH (a:Person)-[r]->(b:Person)
WHERE type(r) IN $relationship_types
  AND {TEMPORAL_RELATIONSHIP_FILTER}
RETURN gds.graph.project(
  $graph_name,
  a,
  b,
  {{ relationshipType: type(r) }},
  {{
    sessionId: $session_id,
    undirectedRelationshipTypes: $relationship_types
  }}
)
"""

PAGERANK_CYPHER = """
CALL gds.pageRank.stream($graph_name)
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS person, score
RETURN person.person_id AS entity_id, person.name AS name, score AS pagerank
ORDER BY pagerank DESC
"""

LOUVAIN_CYPHER = """
CALL gds.louvain.stream($graph_name)
YIELD nodeId, communityId
WITH gds.util.asNode(nodeId) AS person, communityId
RETURN person.person_id AS entity_id, person.name AS name, communityId
ORDER BY communityId, entity_id
"""

SEED_NODE_IDS_CYPHER = """
MATCH (seed:Person)
WHERE seed.person_id IN $seed_ids
RETURN collect(id(seed)) AS source_node_ids, collect(seed.person_id) AS matched_seed_ids
"""

PERSONALIZED_PAGERANK_CYPHER = """
CALL gds.pageRank.stream($graph_name, {
  sourceNodes: $source_node_ids,
  dampingFactor: 0.85,
  maxIterations: 20
})
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS person, score
RETURN person.person_id AS entity_id, person.name AS name, score AS personalized_pagerank
ORDER BY personalized_pagerank DESC
"""


class GdsUnavailableError(Neo4jUnavailableError):
    """Raised when Aura Graph Analytics / GDS is unavailable."""


def is_graph_already_exists_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "graphalreadyexists" in message or (
        "already exists" in message and "graph" in message
    )


def is_missing_graph_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "does not exist" in message
        or "could not be found" in message
        or "no graph store" in message
    )


def build_native_projection_parameters(
    graph_name: str,
    session_id: str,
) -> dict[str, Any]:
    """Build Aura-compatible native projection parameters."""
    relationship_types = list(PERSON_RELATIONSHIP_TYPES)
    return {
        "graph_name": graph_name,
        "relationship_types": relationship_types,
        "session_id": session_id,
    }


def build_temporal_projection_parameters(
    graph_name: str,
    session_id: str,
    *,
    from_datetime: str | None,
    to_datetime: str | None,
) -> dict[str, Any]:
    """Build Aura-compatible temporal Cypher projection parameters."""
    return {
        "graph_name": graph_name,
        "relationship_types": list(PERSON_RELATIONSHIP_TYPES),
        "session_id": session_id,
        "from_datetime": from_datetime,
        "to_datetime": to_datetime,
    }


def parse_projection_stats(rows: list[dict[str, Any]], *, graph_name: str) -> dict[str, Any]:
    if not rows:
        raise GdsUnavailableError("Failed to create CNAS person graph projection")

    row = rows[0]
    if row.get("graphName") is not None:
        stats_row = row
    else:
        stats_row = next(
            (
                value
                for value in row.values()
                if isinstance(value, dict) and value.get("graphName") is not None
            ),
            None,
        )
        if stats_row is None:
            raise GdsUnavailableError("Failed to create CNAS person graph projection")

    return {
        "graph_name": stats_row.get("graphName", graph_name),
        "node_count": stats_row.get("nodeCount", 0),
        "relationship_count": stats_row.get("relationshipCount", 0),
        "project_millis": stats_row.get("projectMillis", 0),
    }


def normalize_seed_person_ids(seed_person_ids: list[str]) -> list[str]:
    return [seed.strip() for seed in seed_person_ids if seed and seed.strip()]


def normalize_temporal_window(
    from_datetime: str | None,
    to_datetime: str | None,
) -> dict[str, str | None] | None:
    if not from_datetime and not to_datetime:
        return None

    if from_datetime and to_datetime and from_datetime > to_datetime:
        raise ValueError("from_datetime must be before or equal to to_datetime")

    return {
        "from_datetime": from_datetime,
        "to_datetime": to_datetime,
    }


def time_window_payload(
    from_datetime: str | None = None,
    to_datetime: str | None = None,
) -> dict[str, Any]:
    window = normalize_temporal_window(from_datetime, to_datetime)
    if window is None:
        return {
            "applied": False,
            "from_datetime": None,
            "to_datetime": None,
        }

    return {
        "applied": True,
        **window,
    }


def projection_graph_name(
    from_datetime: str | None = None,
    to_datetime: str | None = None,
) -> str:
    if normalize_temporal_window(from_datetime, to_datetime) is None:
        return GRAPH_PROJECTION_NAME
    return TEMPORAL_GRAPH_PROJECTION_NAME


def _run_gds(cypher: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    try:
        return run_cypher(cypher, parameters or {})
    except Neo4jUnavailableError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface GDS failures to API layer
        message = str(exc)
        if "Unknown function" in message or "gds." in message.lower() and "not" in message.lower():
            raise GdsUnavailableError(
                "Neo4j Graph Data Science (GDS) is not available on this Aura instance"
            ) from exc
        raise GdsUnavailableError(message) from exc


def ensure_gds_session() -> dict[str, Any]:
    """Get or create the Aura Graph Analytics session used for CNAS projections."""
    settings = gds_session_settings()
    rows = _run_gds(
        SESSION_GET_OR_CREATE_CYPHER,
        {
            "session_name": settings["name"],
            "memory": settings["memory"],
            "ttl_minutes": settings["ttl_minutes"],
        },
    )
    if not rows or not rows[0].get("id"):
        raise GdsUnavailableError("Failed to create Aura Graph Analytics session")

    session = rows[0]
    return {
        "session_id": session["id"],
        "session_name": session.get("name", settings["name"]),
        "memory": session.get("memory", settings["memory"]),
        "status": session.get("status"),
    }


def drop_graph_projection(graph_name: str) -> bool:
    """Drop a projection when present; safe when the graph is already absent."""
    try:
        rows = _run_gds(DROP_GRAPH_CYPHER, {"graph_name": graph_name})
        return bool(rows)
    except GdsUnavailableError as exc:
        if is_missing_graph_error(exc):
            return False
        raise


def drop_all_cnas_graph_projections() -> None:
    """Remove all CNAS temporary analytics projections from the active GDS session."""
    for graph_name in CNAS_GRAPH_PROJECTION_NAMES:
        drop_graph_projection(graph_name)


def graph_projection_exists(graph_name: str) -> bool:
    rows = _run_gds(GRAPH_EXISTS_CYPHER, {"graph_name": graph_name})
    return bool(rows and rows[0].get("exists"))


def _create_person_graph_projection(
    graph_name: str,
    session_id: str,
    window: dict[str, str | None] | None,
    *,
    from_datetime: str | None,
    to_datetime: str | None,
) -> dict[str, Any]:
    if window is None:
        cypher = PROJECT_GRAPH_CYPHER
        parameters = build_native_projection_parameters(graph_name, session_id)
    else:
        cypher = PROJECT_GRAPH_CYPHER_TEMPORAL
        parameters = build_temporal_projection_parameters(
            graph_name,
            session_id,
            from_datetime=window["from_datetime"],
            to_datetime=window["to_datetime"],
        )

    last_error: GdsUnavailableError | None = None
    for attempt in range(2):
        drop_graph_projection(graph_name)
        try:
            rows = _run_gds(cypher, parameters)
            return parse_projection_stats(rows, graph_name=graph_name)
        except GdsUnavailableError as exc:
            last_error = exc
            if is_graph_already_exists_error(exc) and attempt == 0:
                continue
            raise

    if last_error is not None:
        raise last_error
    raise GdsUnavailableError("Failed to create CNAS person graph projection")


def ensure_person_graph_projection(
    *,
    from_datetime: str | None = None,
    to_datetime: str | None = None,
) -> dict[str, Any]:
    """Create or refresh the in-memory Person analytics projection."""
    with _projection_lock:
        return _ensure_person_graph_projection_unlocked(
            from_datetime=from_datetime,
            to_datetime=to_datetime,
        )


def _ensure_person_graph_projection_unlocked(
    *,
    from_datetime: str | None = None,
    to_datetime: str | None = None,
) -> dict[str, Any]:
    window = normalize_temporal_window(from_datetime, to_datetime)
    graph_name = projection_graph_name(from_datetime, to_datetime)
    session = ensure_gds_session()

    drop_all_cnas_graph_projections()
    stats = _create_person_graph_projection(
        graph_name,
        session["session_id"],
        window,
        from_datetime=from_datetime,
        to_datetime=to_datetime,
    )

    stats["session"] = session
    stats["time_window"] = time_window_payload(from_datetime, to_datetime)
    return stats


def calculate_person_pagerank(
    *,
    refresh_projection: bool = True,
    from_datetime: str | None = None,
    to_datetime: str | None = None,
) -> dict[str, Any]:
    graph_name = projection_graph_name(from_datetime, to_datetime)
    time_window = time_window_payload(from_datetime, to_datetime)

    if refresh_projection:
        with _projection_lock:
            projection = _ensure_person_graph_projection_unlocked(
                from_datetime=from_datetime,
                to_datetime=to_datetime,
            )
            rows = (
                _run_gds(PAGERANK_CYPHER, {"graph_name": graph_name})
                if projection.get("relationship_count", 1) > 0
                else []
            )
    else:
        projection = {"graph_name": graph_name, "time_window": time_window}
        rows = (
            _run_gds(PAGERANK_CYPHER, {"graph_name": graph_name})
            if projection.get("relationship_count", 1) > 0
            else []
        )
    data = []
    for index, row in enumerate(rows, start=1):
        data.append(
            {
                "entity_id": row.get("entity_id"),
                "name": row.get("name"),
                "pagerank": round(float(row.get("pagerank") or 0), 4),
                "rank": index,
            }
        )

    return {
        "total": len(data),
        "method": "gds.pageRank",
        "graph_projection": projection.get("graph_name", graph_name),
        "projection_stats": projection,
        "time_window": time_window,
        "data": data,
    }


def detect_person_communities(
    *,
    refresh_projection: bool = True,
    from_datetime: str | None = None,
    to_datetime: str | None = None,
) -> dict[str, Any]:
    graph_name = projection_graph_name(from_datetime, to_datetime)
    time_window = time_window_payload(from_datetime, to_datetime)

    if refresh_projection:
        with _projection_lock:
            projection = _ensure_person_graph_projection_unlocked(
                from_datetime=from_datetime,
                to_datetime=to_datetime,
            )
            rows = (
                _run_gds(LOUVAIN_CYPHER, {"graph_name": graph_name})
                if projection.get("relationship_count", 1) > 0
                else []
            )
    else:
        projection = {"graph_name": graph_name, "time_window": time_window}
        rows = (
            _run_gds(LOUVAIN_CYPHER, {"graph_name": graph_name})
            if projection.get("relationship_count", 1) > 0
            else []
        )
    grouped: dict[int, list[dict[str, Any]]] = {}

    for row in rows:
        community_id = int(row.get("communityId", 0))
        grouped.setdefault(community_id, []).append(
            {
                "entity_id": row.get("entity_id"),
                "name": row.get("name"),
            }
        )

    communities = []
    for raw_id, members in sorted(grouped.items(), key=lambda item: len(item[1]), reverse=True):
        communities.append(
            {
                "community_id": raw_id,
                "size": len(members),
                "members": members,
            }
        )

    for index, community in enumerate(communities, start=1):
        community["display_id"] = index

    return {
        "total_communities": len(communities),
        "method": "gds.louvain",
        "graph_projection": projection.get("graph_name", graph_name),
        "projection_stats": projection,
        "time_window": time_window,
        "communities": communities,
    }


def calculate_personalized_pagerank(
    seed_person_ids: list[str],
    *,
    refresh_projection: bool = True,
) -> dict[str, Any]:
    seeds = normalize_seed_person_ids(seed_person_ids)
    if not seeds:
        raise ValueError("At least one seed person ID is required")

    if refresh_projection:
        with _projection_lock:
            projection = _ensure_person_graph_projection_unlocked()
            seed_rows = _run_gds(SEED_NODE_IDS_CYPHER, {"seed_ids": seeds})
            if not seed_rows:
                raise ValueError("No matching seed persons were found in the graph")

            source_node_ids = seed_rows[0].get("source_node_ids") or []
            matched_seed_ids = seed_rows[0].get("matched_seed_ids") or []
            if not source_node_ids:
                raise ValueError("No matching seed persons were found in the graph")

            rows = _run_gds(
                PERSONALIZED_PAGERANK_CYPHER,
                {
                    "graph_name": GRAPH_PROJECTION_NAME,
                    "source_node_ids": source_node_ids,
                },
            )
    else:
        projection = {"graph_name": GRAPH_PROJECTION_NAME}
        seed_rows = _run_gds(SEED_NODE_IDS_CYPHER, {"seed_ids": seeds})
        if not seed_rows:
            raise ValueError("No matching seed persons were found in the graph")

        source_node_ids = seed_rows[0].get("source_node_ids") or []
        matched_seed_ids = seed_rows[0].get("matched_seed_ids") or []
        if not source_node_ids:
            raise ValueError("No matching seed persons were found in the graph")

        rows = _run_gds(
            PERSONALIZED_PAGERANK_CYPHER,
            {
                "graph_name": GRAPH_PROJECTION_NAME,
                "source_node_ids": source_node_ids,
            },
        )

    data = []
    for index, row in enumerate(rows, start=1):
        data.append(
            {
                "entity_id": row.get("entity_id"),
                "name": row.get("name"),
                "personalized_pagerank": round(float(row.get("personalized_pagerank") or 0), 4),
                "rank": index,
            }
        )

    return {
        "total": len(data),
        "method": "gds.pageRank.personalized",
        "seeds": matched_seed_ids,
        "graph_projection": projection.get("graph_name", GRAPH_PROJECTION_NAME),
        "projection_stats": projection,
        "data": data,
    }
