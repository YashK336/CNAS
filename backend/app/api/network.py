import math
from typing import Any

from fastapi import APIRouter, Query

from app.services.graph.importer import import_cnas_graph
from app.services.graph_builder import build_criminal_network
from app.services.neo4j_client import verify_neo4j_connectivity
from app.services.normalization import clean_cell


router = APIRouter(
    prefix="/network",
    tags=["Network"]
)


def _json_safe_value(value: Any) -> Any:
    cleaned = clean_cell(value)
    if isinstance(cleaned, float) and not math.isfinite(cleaned):
        return None
    return cleaned


def _json_safe_attrs(data: dict[str, Any]) -> dict[str, Any]:
    return {str(key): _json_safe_value(value) for key, value in data.items()}


@router.get("/summary")
def get_network_summary():

    G = build_criminal_network()

    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges()
    }


@router.get("/graph")
def get_network_graph():

    G = build_criminal_network()

    nodes = []

    for node_id, data in G.nodes(data=True):
        safe_id = _json_safe_value(node_id)
        if safe_id is None:
            continue
        nodes.append({
            "id": safe_id,
            **_json_safe_attrs(data),
        })

    edges = []

    for source, target, data in G.edges(data=True):
        safe_source = _json_safe_value(source)
        safe_target = _json_safe_value(target)
        if safe_source is None or safe_target is None:
            continue
        edges.append({
            "source": safe_source,
            "target": safe_target,
            **_json_safe_attrs(data),
        })

    return {
        "nodes": nodes,
        "edges": edges
    }


@router.get("/neo4j-health")
def get_neo4j_health():
    return verify_neo4j_connectivity()


@router.post("/neo4j-import")
def trigger_neo4j_import(dry_run: bool = Query(default=False)):
    """Import the canonical CNAS graph into AuraDB. Use dry_run=true to preview counts only."""
    return import_cnas_graph(dry_run=dry_run)