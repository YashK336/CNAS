"""Evidence-backed explanations for graph-aware risk results."""

from __future__ import annotations

from typing import Any

from app.services.analytics import _normalize_graph_seeds
from app.services.neo4j_analytics import (
    Neo4jUnavailableError,
    PersonNotFoundError,
    query_person_path,
)


def _entity_type_from_labels(labels: list[str]) -> str | None:
    if not labels:
        return None
    return labels[0].lower()


def _format_evidence_node(node: dict[str, Any]) -> dict[str, Any]:
    properties = node.get("properties") or {}
    labels = node.get("labels") or []
    return {
        "entity_id": node.get("id"),
        "entity_type": _entity_type_from_labels(labels),
        "name": properties.get("name"),
    }


def _format_evidence_relationship(relationship: dict[str, Any]) -> dict[str, Any]:
    properties = relationship.get("properties") or {}
    provenance = relationship.get("provenance") or {}
    return {
        "type": relationship.get("type"),
        "source": relationship.get("source"),
        "target": relationship.get("target"),
        "provenance": {
            "source": provenance.get("source"),
            "source_ref": provenance.get("source_ref"),
            "content_hash": provenance.get("content_hash"),
            "ingested_at": provenance.get("ingested_at"),
        },
    }


def _build_seed_person_evidence(person_id: str, seed_id: str) -> dict[str, Any]:
    return {
        "seed_id": seed_id,
        "found": True,
        "is_seed_person": True,
        "degrees_of_separation": 0,
        "nodes": [
            {
                "entity_id": person_id,
                "entity_type": "person",
                "name": None,
            }
        ],
        "relationships": [],
    }


def _build_path_evidence(seed_id: str, path_result: dict[str, Any]) -> dict[str, Any]:
    nodes = [_format_evidence_node(node) for node in path_result.get("nodes", [])]
    relationships = [
        _format_evidence_relationship(relationship)
        for relationship in path_result.get("relationships", [])
    ]
    return {
        "seed_id": seed_id,
        "found": True,
        "is_seed_person": False,
        "degrees_of_separation": max(len(nodes) - 1, 0),
        "nodes": nodes,
        "relationships": relationships,
    }


def _build_missing_path_evidence(seed_id: str, message: str) -> dict[str, Any]:
    return {
        "seed_id": seed_id,
        "found": False,
        "is_seed_person": False,
        "message": message,
        "degrees_of_separation": None,
        "nodes": [],
        "relationships": [],
    }


def get_risk_graph_evidence(
    person_id: str,
    graph_seeds: list[str] | None,
    *,
    max_depth: int = 6,
) -> dict[str, Any]:
    """
    Return graph evidence chains connecting a person to supplied risk seeds.

    Uses existing Neo4j shortest-path investigation queries and returns only
    relationships observed in the persisted graph.
    """
    seeds = _normalize_graph_seeds(graph_seeds)
    if not seeds:
        raise ValueError("graph_seeds are required for risk evidence")

    propagation_chains: list[dict[str, Any]] = []

    for seed_id in seeds:
        if str(seed_id) == str(person_id):
            propagation_chains.append(_build_seed_person_evidence(person_id, seed_id))
            continue

        try:
            path_result = query_person_path(
                seed_id,
                person_id,
                max_depth=max_depth,
            )
        except PersonNotFoundError:
            raise
        except Neo4jUnavailableError:
            propagation_chains.append(
                _build_missing_path_evidence(
                    seed_id,
                    "Neo4j graph evidence is unavailable",
                )
            )
            continue

        if path_result.get("found"):
            propagation_chains.append(_build_path_evidence(seed_id, path_result))
        else:
            propagation_chains.append(
                _build_missing_path_evidence(
                    seed_id,
                    path_result.get("message", "No path between the selected persons"),
                )
            )

    return {
        "entity_id": person_id,
        "graph_seeds": seeds,
        "evidence": {
            "graph_propagation": propagation_chains,
        },
    }
