from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from app.services.an2_input import parse_an2_input
from app.services.analytics import (
    anomaly_distribution,
    calculate_anomalies,
    calculate_centrality,
    calculate_risk,
    detect_communities,
    find_connection,
    network_statistics,
)
from app.services.graph_builder import build_criminal_network
from app.services.neo4j_analytics import Neo4jUnavailableError, PersonNotFoundError
from app.services.risk_evidence import get_risk_graph_evidence
from app.services.identifier_recurrence import detect_identifier_recurrence
from app.services.unstructured_ingestion import ingest_unstructured_fir


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)


def _parse_graph_seeds(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    seeds = [item.strip() for item in raw.split(",") if item.strip()]
    return seeds or None


@router.get("/centrality")
def get_centrality():

    G = build_criminal_network()

    results = calculate_centrality(G)

    return {
        "total": len(results),
        "data": results
    }


@router.get("/statistics")
def get_statistics():

    G = build_criminal_network()

    return network_statistics(G)


@router.get("/communities")
def get_communities():
    G = build_criminal_network()
    results = detect_communities(G)

    return {
        "total": len(results),
        "data": results
    }


@router.get("/key-persons")
def get_key_persons():

    G = build_criminal_network()

    results = calculate_centrality(G)

    return {
        "total": len(results),
        "data": results[:10]
    }


@router.get("/connection/{source_id}/{target_id}")
def get_connection(source_id: str, target_id: str):
    G = build_criminal_network()

    return find_connection(
        G,
        source_id,
        target_id
    )


@router.get("/risk")
def get_risk_scores(graph_seeds: str | None = Query(default=None)):
    G = build_criminal_network()
    results = calculate_risk(G, graph_seeds=_parse_graph_seeds(graph_seeds))

    return {
        "total": len(results),
        "data": results
    }


@router.get("/risk/{person_id}")
def get_person_risk(
    person_id: str,
    graph_seeds: str | None = Query(default=None),
):
    G = build_criminal_network()
    results = calculate_risk(G, graph_seeds=_parse_graph_seeds(graph_seeds))

    for person in results:
        if str(person.get("entity_id")) == str(person_id):
            return person

    raise HTTPException(
        status_code=404,
        detail="Person not found"
    )


@router.get("/risk/{person_id}/evidence")
def get_person_risk_evidence(
    person_id: str,
    graph_seeds: str = Query(..., min_length=1),
    max_depth: int = Query(default=6, ge=1, le=6),
):
    G = build_criminal_network()
    if person_id not in G or G.nodes[person_id].get("entity_type") != "person":
        raise HTTPException(status_code=404, detail="Person not found")

    try:
        return get_risk_graph_evidence(
            person_id,
            _parse_graph_seeds(graph_seeds),
            max_depth=max_depth,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PersonNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Neo4jUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/anomalies")
def get_anomalies():
    G = build_criminal_network()
    profiles = calculate_anomalies(G)
    summary = anomaly_distribution(profiles)

    return {
        "total": summary["total_people"],
        "distribution": summary["distribution"],
        "data": profiles,
    }


@router.get("/anomalies/{person_id}")
def get_person_anomaly(person_id: str):
    G = build_criminal_network()
    profiles = calculate_anomalies(G)

    for profile in profiles:
        if str(profile.get("entity_id")) == str(person_id):
            return profile

    raise HTTPException(
        status_code=404,
        detail="Person not found"
    ) 


@router.post("/findings/an-2")
def get_an2_identifier_recurrence(payload: Any = Body(...)):
    """Detect AN-2 recurrence across supplied unstructured FIR documents."""
    try:
        records = [ingest_unstructured_fir(item) for item in parse_an2_input(payload)]
        findings = detect_identifier_recurrence(records)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "finding_type": "AN-2",
        "total": len(findings),
        "data": findings,
    }
@router.get("/communities")
def get_communities():
    G = build_criminal_network()

    return detect_communities(G)
