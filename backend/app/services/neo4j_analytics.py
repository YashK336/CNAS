"""Neo4j-backed investigation queries over the persisted CNAS graph."""

from __future__ import annotations

from typing import Any

from app.core import config
from app.services.graph.ontology import (
    REL_AT_LOCATION,
    REL_ASSOCIATED_WITH,
    REL_CALLED,
    REL_CO_ACCUSED_IN,
    REL_FOR_CRIME,
    REL_HAS_ACCOUNT,
    REL_HAS_PHONE,
    REL_HAS_SOCIAL_ACCOUNT,
    REL_INTERACTED_WITH,
    REL_INVOLVED_IN,
    REL_OBSERVED_AT,
    REL_OWNS,
    REL_PRESENT_AT,
    REL_SHARES_IDENTIFIER,
    REL_TRANSFERRED_MONEY_TO,
    REL_TRANSACTED_WITH,
    REL_USES,
    REL_MEMBER_OF,
)
from app.services.neo4j_client import get_neo4j_driver

ALLOWED_RELATIONSHIP_TYPES: frozenset[str] = frozenset(
    {
        REL_HAS_PHONE,
        REL_OWNS,
        REL_HAS_ACCOUNT,
        REL_HAS_SOCIAL_ACCOUNT,
        REL_CALLED,
        REL_TRANSFERRED_MONEY_TO,
        REL_INTERACTED_WITH,
        REL_INVOLVED_IN,
        REL_FOR_CRIME,
        REL_AT_LOCATION,
        REL_OBSERVED_AT,
        REL_PRESENT_AT,
        REL_USES,
        REL_TRANSACTED_WITH,
        REL_CO_ACCUSED_IN,
        REL_ASSOCIATED_WITH,
        REL_MEMBER_OF,
        REL_SHARES_IDENTIFIER,
        "SOCIAL_REPLY",
        "SOCIAL_RETWEET",
        "SOCIAL_MENTION",
    }
)

NODE_KEY_FIELDS: dict[str, str] = {
    "Person": "person_id",
    "Phone": "value",
    "Account": "account_ref",
    "Vehicle": "vehicle_no",
    "BankAccount": "account_id",
    "SocialAccount": "handle",
    "Location": "name",
    "FIR": "fir_id",
    "Case": "case_no",
    "Incident": "incident_id",
    "Crime": "name",
    "SurveillanceEvent": "event_id",
}

MAX_QUERY_DEPTH = 6
DEFAULT_QUERY_DEPTH = 2

TEMPORAL_RELATIONSHIP_FILTER = """
(
  $from_datetime IS NULL
  OR coalesce(rel.valid_from, rel.timestamp, rel.date) IS NULL
  OR coalesce(rel.valid_from, rel.timestamp, rel.date) >= $from_datetime
)
AND (
  $to_datetime IS NULL
  OR coalesce(rel.valid_from, rel.timestamp, rel.date) IS NULL
  OR coalesce(rel.valid_from, rel.timestamp, rel.date) <= $to_datetime
)
"""

PERSON_EXISTS_CYPHER = """
MATCH (person:Person {person_id: $person_id})
RETURN person.person_id AS person_id
"""

NEIGHBORHOOD_CYPHER = f"""
MATCH (center:Person {{person_id: $person_id}})
OPTIONAL MATCH (center)-[rels*1..$max_depth]-(neighbor)
WHERE ALL(rel IN rels WHERE
  ($rel_types IS NULL OR type(rel) IN $rel_types)
  AND {TEMPORAL_RELATIONSHIP_FILTER.replace("rel.", "rel.")}
)
WITH center, collect(DISTINCT neighbor) AS neighbors
WITH [center] + [n IN neighbors WHERE n IS NOT NULL] AS node_bucket
UNWIND node_bucket AS node
WITH collect(DISTINCT node) AS nodes
UNWIND nodes AS left_node
UNWIND nodes AS right_node
WITH nodes, left_node, right_node
WHERE elementId(left_node) <= elementId(right_node)
OPTIONAL MATCH (left_node)-[rel]-(right_node)
WHERE rel IS NOT NULL
  AND ($rel_types IS NULL OR type(rel) IN $rel_types)
  AND {TEMPORAL_RELATIONSHIP_FILTER}
RETURN nodes, collect(DISTINCT rel) AS relationships
"""

PATH_CYPHER = f"""
MATCH (source:Person {{person_id: $source_id}})
MATCH (target:Person {{person_id: $target_id}})
OPTIONAL MATCH path = shortestPath((source)-[rels*1..$max_depth]-(target))
WHERE path IS NOT NULL
  AND ALL(rel IN relationships(path) WHERE
    ($rel_types IS NULL OR type(rel) IN $rel_types)
    AND {TEMPORAL_RELATIONSHIP_FILTER}
  )
RETURN nodes(path) AS nodes, relationships(path) AS relationships
"""


class Neo4jQueryError(Exception):
    """Base error for Neo4j investigation queries."""


class Neo4jUnavailableError(Neo4jQueryError):
    """Raised when AuraDB is not configured or reachable."""


class PersonNotFoundError(Neo4jQueryError):
    """Raised when a requested Person node does not exist."""


def normalize_relationship_types(relationship_types: list[str] | None) -> list[str] | None:
    if not relationship_types:
        return None

    validated = [rel_type for rel_type in relationship_types if rel_type in ALLOWED_RELATIONSHIP_TYPES]
    return validated or None


def clamp_depth(depth: int, *, default: int = DEFAULT_QUERY_DEPTH) -> int:
    if depth <= 0:
        return default
    return min(depth, MAX_QUERY_DEPTH)


def run_cypher(cypher: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
    config.load_env()
    driver = get_neo4j_driver()
    if driver is None:
        raise Neo4jUnavailableError("Neo4j environment variables are not configured")

    with driver.session(database=config.NEO4J_DATABASE) as session:
        return [record.data() for record in session.run(cypher, parameters)]


def _node_identity(node: Any) -> str:
    labels = list(getattr(node, "labels", []))
    properties = dict(node)
    primary_label = labels[0] if labels else "Node"
    key_field = NODE_KEY_FIELDS.get(primary_label)
    if key_field and properties.get(key_field) is not None:
        return str(properties[key_field])
    if primary_label == "Phone" and properties.get("msisdn") is not None:
        return str(properties["msisdn"])
    return str(getattr(node, "element_id", id(node)))


def _extract_provenance(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": properties.get("source"),
        "source_ref": properties.get("source_ref"),
        "content_hash": properties.get("content_hash"),
        "extraction_method": properties.get("extraction_method"),
        "confidence": properties.get("confidence"),
        "valid_from": properties.get("valid_from"),
        "valid_to": properties.get("valid_to"),
        "ingested_at": properties.get("ingested_at"),
        "jurisdiction": properties.get("jurisdiction"),
        "created_by": properties.get("created_by"),
    }


def serialize_node(node: Any) -> dict[str, Any]:
    labels = list(getattr(node, "labels", []))
    properties = dict(node)
    return {
        "id": _node_identity(node),
        "labels": labels,
        "properties": properties,
        "provenance": _extract_provenance(properties),
    }


def serialize_relationship(relationship: Any) -> dict[str, Any]:
    properties = dict(relationship)
    start_node = relationship.start_node
    end_node = relationship.end_node
    return {
        "type": relationship.type,
        "source": _node_identity(start_node),
        "target": _node_identity(end_node),
        "properties": properties,
        "provenance": _extract_provenance(properties),
    }


def _serialize_graph_result(nodes: list[Any], relationships: list[Any]) -> dict[str, Any]:
    serialized_nodes = [serialize_node(node) for node in nodes if node is not None]
    serialized_relationships = [
        serialize_relationship(relationship)
        for relationship in relationships
        if relationship is not None
    ]

    return {
        "nodes": serialized_nodes,
        "relationships": serialized_relationships,
        "counts": {
            "nodes": len(serialized_nodes),
            "relationships": len(serialized_relationships),
        },
    }


def _assert_person_exists(person_id: str) -> None:
    rows = run_cypher(PERSON_EXISTS_CYPHER, {"person_id": person_id})
    if not rows:
        raise PersonNotFoundError(f"Person '{person_id}' was not found")


def query_person_neighborhood(
    person_id: str,
    *,
    max_depth: int = DEFAULT_QUERY_DEPTH,
    relationship_types: list[str] | None = None,
    from_datetime: str | None = None,
    to_datetime: str | None = None,
) -> dict[str, Any]:
    _assert_person_exists(person_id)

    parameters = {
        "person_id": person_id,
        "max_depth": clamp_depth(max_depth),
        "rel_types": normalize_relationship_types(relationship_types),
        "from_datetime": from_datetime,
        "to_datetime": to_datetime,
    }
    rows = run_cypher(NEIGHBORHOOD_CYPHER, parameters)
    if not rows:
        return {
            "center_id": person_id,
            "depth": parameters["max_depth"],
            "filters": _filters_payload(parameters),
            "nodes": [],
            "relationships": [],
            "counts": {"nodes": 0, "relationships": 0},
        }

    row = rows[0]
    graph = _serialize_graph_result(row.get("nodes") or [], row.get("relationships") or [])
    graph.update(
        {
            "center_id": person_id,
            "depth": parameters["max_depth"],
            "filters": _filters_payload(parameters),
        }
    )
    return graph


def query_person_path(
    source_id: str,
    target_id: str,
    *,
    max_depth: int = DEFAULT_QUERY_DEPTH,
    relationship_types: list[str] | None = None,
    from_datetime: str | None = None,
    to_datetime: str | None = None,
) -> dict[str, Any]:
    _assert_person_exists(source_id)
    _assert_person_exists(target_id)

    parameters = {
        "source_id": source_id,
        "target_id": target_id,
        "max_depth": clamp_depth(max_depth),
        "rel_types": normalize_relationship_types(relationship_types),
        "from_datetime": from_datetime,
        "to_datetime": to_datetime,
    }
    rows = run_cypher(PATH_CYPHER, parameters)

    base_payload = {
        "source_id": source_id,
        "target_id": target_id,
        "max_depth": parameters["max_depth"],
        "filters": _filters_payload(parameters),
    }

    if not rows or not rows[0].get("nodes"):
        return {
            **base_payload,
            "found": False,
            "message": "No path between the selected persons",
            "nodes": [],
            "relationships": [],
            "counts": {"nodes": 0, "relationships": 0},
        }

    row = rows[0]
    graph = _serialize_graph_result(row.get("nodes") or [], row.get("relationships") or [])
    graph.update({**base_payload, "found": True})
    return graph


def _filters_payload(parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "relationship_types": parameters.get("rel_types"),
        "from_datetime": parameters.get("from_datetime"),
        "to_datetime": parameters.get("to_datetime"),
    }
