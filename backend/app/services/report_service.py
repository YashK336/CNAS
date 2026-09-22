"""Assemble an investigation report from existing CNAS records.

The payload only restates stored case, person, analytics, AN-2, adjudication,
and provenance data. It does not invent conclusions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.adjudication_authorization import filter_reviews_for_user
from app.services.adjudication_service import _serialize_review
from app.services.analytics import (
    calculate_anomalies,
    calculate_centrality,
    calculate_risk,
    network_statistics,
)
from app.services.auth import serialize_public_user
from app.services.graph_builder import build_criminal_network
from app.services.identifier_recurrence import detect_identifier_recurrence
from app.services.ingestion import (
    dataframe_records,
    load_entity_mapping,
    load_fir,
    load_persons,
    load_vehicles,
)
from app.services.review_repository import get_review_repository
from app.services.user_repository import get_user_repository

STANDARD_LIMITATIONS = [
    "This report restates recorded CNAS data. It does not assert guilt, ownership, or identity beyond stored records.",
    "Empty sections mean no matching records were found in the current CNAS datasets.",
    "Analytics scores are existing rule-based outputs, not investigator conclusions.",
    "AN-2 identifier recurrence is included only when unstructured FIR records are in scope.",
]

RELATIONSHIP_LIMIT = 80
ANALYTICS_LIMIT = 50


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _public_user(user_id: str | None) -> dict[str, Any] | None:
    if not user_id:
        return None
    record = get_user_repository().get_by_id(str(user_id))
    if record is None:
        return None
    return serialize_public_user(record)


def _string_set(values: Any) -> set[str]:
    result: set[str] = set()
    for item in values or []:
        text = str(item).strip()
        if text:
            result.add(text)
    return result


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return None
    return text


def _persons_by_id() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in load_persons().to_dict(orient="records"):
        person_id = _clean(row.get("person_id"))
        if person_id:
            index[person_id] = row
    return index


def _serialize_case(row: dict[str, Any], persons_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    person_id = _clean(row.get("person_id"))
    person = persons_by_id.get(person_id) if person_id else None
    involved = None
    if person is not None:
        involved = {
            "entity_id": _clean(person.get("person_id")),
            "name": _clean(person.get("name")),
            "phone": _clean(person.get("phone")),
            "home_city": _clean(person.get("home_city")),
            "risk_group": _clean(person.get("risk_group")),
        }
    return {
        "fir_id": _clean(row.get("fir_id")),
        "person_id": person_id,
        "crime": _clean(row.get("crime")),
        "date": _clean(row.get("date")),
        "location": _clean(row.get("location")),
        "ingested_at": _clean(row.get("_ingested_at") or row.get("ingested_at")),
        "involved_person": involved,
    }


def _person_records(person_ids: set[str]) -> list[dict[str, Any]]:
    if not person_ids:
        return []
    rows = []
    for row in dataframe_records(load_persons()):
        person_id = str(row.get("person_id") or "").strip()
        if person_id in person_ids:
            rows.append(row)
    return rows


def _case_records(entity_ids: set[str], person_ids: set[str]) -> list[dict[str, Any]]:
    if not entity_ids and not person_ids:
        return []
    persons_by_id = _persons_by_id()
    records = []
    for row in load_fir().to_dict(orient="records"):
        fir_id = str(row.get("fir_id") or "").strip()
        person_id = str(row.get("person_id") or "").strip()
        if fir_id in entity_ids or person_id in person_ids:
            records.append(_serialize_case(row, persons_by_id))
    return records


def _vehicle_records(person_ids: set[str]) -> list[dict[str, Any]]:
    if not person_ids:
        return []
    rows = []
    for row in dataframe_records(load_vehicles()):
        if str(row.get("person_id") or "").strip() in person_ids:
            rows.append(row)
    return rows


def _mapping_evidence(person_ids: set[str]) -> list[dict[str, Any]]:
    if not person_ids:
        return []
    evidence = []
    for row in dataframe_records(load_entity_mapping()):
        entity_id = str(row.get("entity_id") or "").strip()
        if entity_id not in person_ids:
            continue
        evidence.append(
            {
                "source": row.get("source") or "entity_mapping",
                "source_ref": row.get("source_id"),
                "entity_id": entity_id,
                "entity_type": row.get("entity_type"),
                "content_hash": row.get("content_hash"),
                "ingested_at": row.get("_ingested_at") or row.get("ingested_at"),
            }
        )
    return evidence


def _network_summary(entity_ids: set[str], graph) -> dict[str, Any]:
    global_stats = network_statistics(graph)
    if not entity_ids:
        return {
            "in_scope_nodes": 0,
            "in_scope_relationships": 0,
            "relationships": [],
            "global": global_stats,
        }

    neighborhood: set[str] = set()
    for entity_id in entity_ids:
        if entity_id not in graph:
            continue
        neighborhood.add(entity_id)
        neighborhood.update(graph.successors(entity_id))
        neighborhood.update(graph.predecessors(entity_id))

    relationships: list[dict[str, Any]] = []
    for source, target, data in graph.edges(data=True):
        if source not in neighborhood or target not in neighborhood:
            continue
        if source not in entity_ids and target not in entity_ids:
            continue
        relationships.append(
            {
                "source": source,
                "target": target,
                "relationship": data.get("relationship"),
            }
        )
        if len(relationships) >= RELATIONSHIP_LIMIT:
            break

    return {
        "in_scope_nodes": len(neighborhood),
        "in_scope_relationships": len(relationships),
        "relationships": relationships,
        "global": global_stats,
    }


def _filter_analytics(rows: list[dict[str, Any]], person_ids: set[str]) -> list[dict[str, Any]]:
    if not person_ids:
        return []
    matched = [
        row for row in rows if str(row.get("entity_id") or "").strip() in person_ids
    ]
    return matched[:ANALYTICS_LIMIT]


def _an2_findings(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run AN-2 only against unstructured FIR payloads already stored on cases."""
    records = []
    for case in cases:
        narrative = case.get("narrative_text") or case.get("text")
        jurisdiction = case.get("jurisdiction")
        if not narrative or not jurisdiction:
            continue
        records.append(
            {
                "source": "unstructured_fir",
                "source_ref": case.get("fir_id"),
                "jurisdiction": jurisdiction,
                "text": narrative,
            }
        )
    if not records:
        return []
    from app.services.unstructured_ingestion import ingest_unstructured_fir

    normalized = [ingest_unstructured_fir(item) for item in records]
    return detect_identifier_recurrence(normalized)


def _relevant_reviews(
    user: dict[str, Any],
    *,
    person_ids: set[str],
    names: set[str],
    phones: set[str],
) -> list[dict[str, Any]]:
    visible = filter_reviews_for_user(user, get_review_repository().list_all())
    relevant = []
    for record in visible:
        proposed = {str(item) for item in (record.get("proposed_entity_ids") or [])}
        confirmed = str(record.get("confirmed_entity_id") or "").strip()
        candidate = str(record.get("candidate_value") or "").strip()
        if (
            proposed & person_ids
            or confirmed in person_ids
            or candidate in names
            or candidate in phones
        ):
            relevant.append(_serialize_review(record))
    return relevant


def _assemble_report(
    *,
    user: dict[str, Any],
    source_type: str,
    source_id: str,
    investigation: dict[str, Any] | None,
    entity_ids: set[str],
    graph_seeds: list[str],
    jurisdiction: str | None,
    investigator: dict[str, Any] | None,
) -> dict[str, Any]:
    known_people = {
        str(row.get("person_id") or "").strip()
        for row in dataframe_records(load_persons())
        if row.get("person_id")
    }
    person_ids = {entity_id for entity_id in entity_ids if entity_id in known_people}
    cases = _case_records(entity_ids, person_ids)
    for case in cases:
        person_id = str(case.get("person_id") or "").strip()
        if person_id:
            person_ids.add(person_id)
            entity_ids.add(person_id)
        fir_id = str(case.get("fir_id") or "").strip()
        if fir_id:
            entity_ids.add(fir_id)

    people = _person_records(person_ids)
    names = {str(row.get("name") or "").strip() for row in people if row.get("name")}
    phones = {str(row.get("phone") or "").strip() for row in people if row.get("phone")}
    vehicles = _vehicle_records(person_ids)

    graph = build_criminal_network()
    network = _network_summary(entity_ids, graph)
    seeds = [seed for seed in graph_seeds if seed]
    analytics = {
        "risk": _filter_analytics(calculate_risk(graph, graph_seeds=seeds or None), person_ids),
        "anomalies": _filter_analytics(calculate_anomalies(graph), person_ids),
        "centrality": _filter_analytics(calculate_centrality(graph), person_ids),
    }
    an2_findings = _an2_findings(cases)
    reviews = _relevant_reviews(user, person_ids=person_ids, names=names, phones=phones)

    evidence = []
    for case in cases:
        evidence.append(
            {
                "source": "fir",
                "source_ref": case.get("fir_id"),
                "content_hash": None,
                "ingested_at": case.get("ingested_at"),
                "person_id": case.get("person_id"),
            }
        )
    evidence.extend(_mapping_evidence(person_ids))
    for finding in an2_findings:
        evidence.extend(finding.get("evidence") or [])

    limitations = list(STANDARD_LIMITATIONS)
    if not cases:
        limitations.append("No FIR/case records matched the selected entities.")
    if not people:
        limitations.append("No person records matched the selected entities.")
    if not an2_findings:
        limitations.append("No unstructured FIR records were available, so AN-2 findings were not generated.")
    if not reviews:
        limitations.append("No adjudication decisions referenced the selected people or identifiers.")

    confidence: dict[str, Any] = {
        "analytics_included": bool(analytics["risk"] or analytics["anomalies"]),
        "an2_finding_count": len(an2_findings),
        "adjudication_decision_count": len(reviews),
    }
    if an2_findings:
        confidence["an2_min_confidence"] = min(
            finding.get("confidence") for finding in an2_findings if finding.get("confidence") is not None
        )

    return {
        "report_id": str(uuid.uuid4()),
        "generated_at": _utc_now_iso(),
        "generated_by": serialize_public_user(user),
        "source": {"type": source_type, "id": source_id},
        "investigation": investigation,
        "investigator": investigator,
        "jurisdiction": jurisdiction,
        "cases": cases,
        "people": people,
        "entities": {
            "vehicles": vehicles,
            "selected_entity_ids": sorted(entity_ids),
        },
        "network_summary": network,
        "analytics": analytics,
        "an2_findings": an2_findings,
        "adjudication": reviews,
        "evidence": evidence,
        "confidence": confidence,
        "limitations": limitations,
    }


def build_investigation_report(
    investigation: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    entity_ids = _string_set(investigation.get("selected_entity_ids")) | _string_set(
        investigation.get("graph_seeds")
    )
    return _assemble_report(
        user=user,
        source_type="investigation",
        source_id=str(investigation.get("id")),
        investigation=investigation,
        entity_ids=entity_ids,
        graph_seeds=list(investigation.get("graph_seeds") or []),
        jurisdiction=investigation.get("jurisdiction"),
        investigator=_public_user(investigation.get("created_by")),
    )


def build_case_report(fir_id: str, user: dict[str, Any]) -> dict[str, Any] | None:
    persons_by_id = _persons_by_id()
    case = None
    for row in load_fir().to_dict(orient="records"):
        if str(row.get("fir_id") or "") == str(fir_id):
            case = _serialize_case(row, persons_by_id)
            break
    if case is None:
        return None
    entity_ids = _string_set([case.get("fir_id"), case.get("person_id")])
    investigation = {
        "id": None,
        "name": f"Case {case.get('fir_id')}",
        "description": None,
        "selected_entity_ids": sorted(entity_ids),
        "graph_seeds": [case["person_id"]] if case.get("person_id") else [],
        "from_datetime": case.get("date"),
        "to_datetime": case.get("date"),
        "created_by": None,
        "jurisdiction": None,
        "created_at": case.get("ingested_at"),
        "updated_at": case.get("ingested_at"),
    }
    return _assemble_report(
        user=user,
        source_type="case",
        source_id=str(fir_id),
        investigation=investigation,
        entity_ids=entity_ids,
        graph_seeds=investigation["graph_seeds"],
        jurisdiction=None,
        investigator=None,
    )
