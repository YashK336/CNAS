from fastapi import APIRouter, HTTPException, Query

from app.services.neo4j_analytics import (
    Neo4jUnavailableError,
    PersonNotFoundError,
    query_person_neighborhood,
    query_person_path,
)
from app.services.neo4j_gds_analytics import (
    GdsUnavailableError,
    calculate_person_pagerank,
    calculate_personalized_pagerank,
    detect_person_communities,
)

router = APIRouter(
    prefix="/neo4j",
    tags=["Neo4j Analytics"],
)


def _parse_relationship_types(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_seed_person_ids(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


@router.get("/neighborhood/{person_id}")
def get_person_neighborhood(
    person_id: str,
    depth: int = Query(default=2, ge=1, le=6),
    relationship_types: str | None = Query(default=None),
    from_datetime: str | None = Query(default=None),
    to_datetime: str | None = Query(default=None),
):
    try:
        return query_person_neighborhood(
            person_id,
            max_depth=depth,
            relationship_types=_parse_relationship_types(relationship_types),
            from_datetime=from_datetime,
            to_datetime=to_datetime,
        )
    except PersonNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Neo4jUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/path/{source_id}/{target_id}")
def get_person_path(
    source_id: str,
    target_id: str,
    max_depth: int = Query(default=6, ge=1, le=6),
    relationship_types: str | None = Query(default=None),
    from_datetime: str | None = Query(default=None),
    to_datetime: str | None = Query(default=None),
):
    try:
        return query_person_path(
            source_id,
            target_id,
            max_depth=max_depth,
            relationship_types=_parse_relationship_types(relationship_types),
            from_datetime=from_datetime,
            to_datetime=to_datetime,
        )
    except PersonNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Neo4jUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/pagerank")
def get_neo4j_pagerank(
    refresh_projection: bool = Query(default=True),
    from_datetime: str | None = Query(default=None),
    to_datetime: str | None = Query(default=None),
):
    try:
        return calculate_person_pagerank(
            refresh_projection=refresh_projection,
            from_datetime=from_datetime,
            to_datetime=to_datetime,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GdsUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Neo4jUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/personalized-pagerank")
def get_neo4j_personalized_pagerank(
    seeds: str = Query(..., min_length=1),
    refresh_projection: bool = Query(default=True),
):
    try:
        return calculate_personalized_pagerank(
            _parse_seed_person_ids(seeds),
            refresh_projection=refresh_projection,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GdsUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Neo4jUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/communities")
def get_neo4j_communities(
    refresh_projection: bool = Query(default=True),
    from_datetime: str | None = Query(default=None),
    to_datetime: str | None = Query(default=None),
):
    try:
        return detect_person_communities(
            refresh_projection=refresh_projection,
            from_datetime=from_datetime,
            to_datetime=to_datetime,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GdsUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Neo4jUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
