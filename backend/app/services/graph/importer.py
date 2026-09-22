"""Execute CNAS graph plans against Neo4j AuraDB using idempotent MERGE operations."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Iterable

from app.core.config import NEO4J_DATABASE
from app.services.graph.mapper import GraphPlan, NodeSpec, RelationshipSpec, build_cnas_graph_plan
from app.services.graph.ontology import (
    CANONICAL_UNIQUE_CONSTRAINTS,
    CANONICAL_RELATIONSHIP_TYPES,
    UNIQUE_CONSTRAINTS,
    validate_edge_provenance,
)
from app.services.neo4j_client import get_neo4j_driver


# Keep transactions bounded for Aura while reducing network round trips.
IMPORT_BATCH_SIZE = 500


def constraint_cypher(label: str, key_property: str) -> str:
    constraint_name = f"{label.lower()}_{key_property}_unique"
    return (
        f"CREATE CONSTRAINT {constraint_name} IF NOT EXISTS "
        f"FOR (n:{label}) REQUIRE n.{key_property} IS UNIQUE"
    )


def merge_node_cypher(spec: NodeSpec) -> str:
    return (
        f"MERGE (n:{spec.label} {{{spec.key_property}: $key_value}}) "
        "SET n += $properties"
    )


def merge_relationship_cypher(spec: RelationshipSpec) -> str:
    return (
        f"MATCH (a:{spec.from_label} {{{spec.from_key}: $from_value}}) "
        f"MATCH (b:{spec.to_label} {{{spec.to_key}: $to_value}}) "
        f"MERGE (a)-[r:{spec.rel_type} {{record_id: $record_id}}]->(b) "
        "SET r += $properties"
    )


def batch_merge_node_cypher(spec: NodeSpec) -> str:
    return (
        f"UNWIND $rows AS row "
        f"MERGE (n:{spec.label} {{{spec.key_property}: row.key_value}}) "
        "SET n += row.properties"
    )


def batch_merge_relationship_cypher(spec: RelationshipSpec) -> str:
    return (
        "UNWIND $rows AS row "
        f"MATCH (a:{spec.from_label} {{{spec.from_key}: row.from_value}}) "
        f"MATCH (b:{spec.to_label} {{{spec.to_key}: row.to_value}}) "
        f"MERGE (a)-[r:{spec.rel_type} {{record_id: row.record_id}}]->(b) "
        "SET r += row.properties"
    )


def apply_constraints(session) -> int:
    applied = 0
    for label, key_property in (*UNIQUE_CONSTRAINTS, *CANONICAL_UNIQUE_CONSTRAINTS):
        session.run(constraint_cypher(label, key_property))
        applied += 1
    return applied


def merge_node(session, spec: NodeSpec) -> None:
    session.run(
        merge_node_cypher(spec),
        key_value=spec.key_value,
        properties=spec.properties,
    )


def merge_relationship(session, spec: RelationshipSpec) -> None:
    if spec.from_label in {"Phone", "Account", "Case", "Organisation", "Incident"} or spec.to_label in {
        "Phone", "Account", "Case", "Organisation", "Incident",
    }:
        if spec.rel_type in CANONICAL_RELATIONSHIP_TYPES:
            validate_edge_provenance(spec.properties)
    session.run(
        merge_relationship_cypher(spec),
        from_value=spec.from_value,
        to_value=spec.to_value,
        record_id=spec.record_id,
        properties=spec.properties,
    )


def _chunks(items: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _run_batch(session, query: str, rows: list[dict[str, Any]]) -> None:
    transaction = session.begin_transaction()
    try:
        transaction.run(query, rows=rows)
        transaction.commit()
    except Exception:
        transaction.rollback()
        raise


def merge_nodes_in_batches(session, specs: list[NodeSpec], batch_size: int = IMPORT_BATCH_SIZE) -> int:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    templates: dict[tuple[str, str], NodeSpec] = {}
    for spec in specs:
        group_key = (spec.label, spec.key_property)
        grouped[group_key].append(
            {
                "key_value": spec.key_value,
                "properties": spec.properties,
            }
        )
        templates[group_key] = spec

    for group_key, rows in grouped.items():
        query = batch_merge_node_cypher(templates[group_key])
        for batch in _chunks(rows, batch_size):
            _run_batch(session, query, batch)
    return len(specs)


def merge_relationships_in_batches(
    session,
    specs: list[RelationshipSpec],
    batch_size: int = IMPORT_BATCH_SIZE,
) -> int:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    templates: dict[tuple[str, str, str, str, str], RelationshipSpec] = {}
    for spec in specs:
        if spec.rel_type in CANONICAL_RELATIONSHIP_TYPES and (
            spec.from_label in {"Phone", "Account", "Case", "Organisation", "Incident"}
            or spec.to_label in {"Phone", "Account", "Case", "Organisation", "Incident"}
        ):
            validate_edge_provenance(spec.properties)
        group_key = (
            spec.rel_type,
            spec.from_label,
            spec.from_key,
            spec.to_label,
            spec.to_key,
        )
        grouped[group_key].append(
            {
                "from_value": spec.from_value,
                "to_value": spec.to_value,
                "record_id": spec.record_id,
                "properties": spec.properties,
            }
        )
        templates[group_key] = spec

    for group_key, rows in grouped.items():
        query = batch_merge_relationship_cypher(templates[group_key])
        for batch in _chunks(rows, batch_size):
            _run_batch(session, query, batch)
    return len(specs)


def import_cnas_graph(
    *,
    dry_run: bool = False,
    plan: GraphPlan | None = None,
    session_factory: Callable | None = None,
) -> dict[str, Any]:
    """
    Import the canonical CNAS graph into AuraDB.

    When ``dry_run`` is True, only the planned graph summary is returned.
    """
    graph_plan = plan or build_cnas_graph_plan()

    summary = graph_plan.summary()

    if dry_run:
        return {
            "status": "dry_run",
            "database": NEO4J_DATABASE,
            **summary,
        }

    driver = get_neo4j_driver()
    if driver is None:
        return {
            "status": "unavailable",
            "detail": "Neo4j environment variables are not configured",
            **summary,
        }

    constraints_applied = 0
    nodes_merged = 0
    relationships_merged = 0

    def _execute(session):
        nonlocal constraints_applied, nodes_merged, relationships_merged
        constraints_applied = apply_constraints(session)
        nodes_merged = merge_nodes_in_batches(session, graph_plan.nodes)
        relationships_merged = merge_relationships_in_batches(session, graph_plan.relationships)

    try:
        if session_factory is not None:
            with session_factory() as session:
                _execute(session)
        else:
            with driver.session(database=NEO4J_DATABASE) as session:
                _execute(session)
    except Exception as exc:  # noqa: BLE001 - return import failure to API caller
        return {
            "status": "failed",
            "detail": str(exc),
            "constraints_applied": constraints_applied,
            "nodes_merged": nodes_merged,
            "relationships_merged": relationships_merged,
            **summary,
        }

    return {
        "status": "imported",
        "database": NEO4J_DATABASE,
        "constraints_applied": constraints_applied,
        "nodes_merged": nodes_merged,
        "relationships_merged": relationships_merged,
        **summary,
    }
