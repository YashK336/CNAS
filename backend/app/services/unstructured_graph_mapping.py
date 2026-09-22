"""Map resolved unstructured FIR candidates into a CNAS Neo4j graph plan."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.adjudication_service import create_review_from_resolution
from app.services.entity_resolution import (
    CanonicalRegistry,
    ResolutionResult,
    build_canonical_registry,
    resolve_candidate,
)
from app.services.extraction import (
    EntityCandidate,
    candidate_normalized_value,
    normalize_bank_account,
    normalize_phone,
    normalize_vehicle,
)
from app.services.graph.importer import import_cnas_graph
from app.services.graph.mapper import (
    GraphPlan,
    RelationshipSpec,
    _add_node,
    _add_relationship,
    _canonical_node,
    _canonical_relationship,
    provenance,
)
from app.services.graph.ontology import (
    LABEL_ACCOUNT,
    LABEL_BANK_ACCOUNT,
    LABEL_CASE,
    LABEL_FIR,
    LABEL_INCIDENT,
    LABEL_PERSON,
    LABEL_PHONE,
    LABEL_VEHICLE,
    REL_CO_ACCUSED_IN,
    REL_HAS_ACCOUNT,
    REL_HAS_PHONE,
    REL_INVOLVED_IN,
    REL_OWNS,
    REL_USES,
    validate_edge_provenance,
)
from app.services.normalization import NormalizedRecord
from app.services.resolution_config import (
    RESOLUTION_STATUS_AMBIGUOUS,
    RESOLUTION_STATUS_RESOLVED,
)
from app.services.unstructured_extraction import extract_unified_from_unstructured_record


class UnstructuredGraphValidationError(ValueError):
    """Raised when an unstructured FIR graph plan would violate provenance rules."""


@dataclass
class UnstructuredGraphBuildResult:
    plan: GraphPlan
    resolution_results: list[ResolutionResult] = field(default_factory=list)
    resolved: list[tuple[EntityCandidate, ResolutionResult]] = field(default_factory=list)
    skipped: list[tuple[EntityCandidate, ResolutionResult]] = field(default_factory=list)
    queued_reviews: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {
            **self.plan.summary(),
            "resolved_candidates": len(self.resolved),
            "skipped_candidates": len(self.skipped),
            "queued_reviews": len(self.queued_reviews),
        }


_IDENTIFIER_MAPPING: dict[str, tuple[str, str, Any, str, str, str]] = {
    "phone": (
        LABEL_PHONE,
        "value",
        normalize_phone,
        REL_HAS_PHONE,
        LABEL_PHONE,
        "msisdn",
    ),
    "vehicle": (
        LABEL_VEHICLE,
        "vehicle_no",
        normalize_vehicle,
        REL_OWNS,
        LABEL_VEHICLE,
        "registration_no",
    ),
    "bank_account": (
        LABEL_BANK_ACCOUNT,
        "account_id",
        normalize_bank_account,
        REL_HAS_ACCOUNT,
        LABEL_ACCOUNT,
        "account_ref",
    ),
}


def _require_unstructured_record(record: NormalizedRecord) -> tuple[str, str]:
    data = record["data"]
    source_ref = data.get("source_ref")
    jurisdiction = data.get("jurisdiction")
    text = data.get("text")

    if not isinstance(text, str) or not text.strip():
        raise UnstructuredGraphValidationError("unstructured FIR record requires non-empty text")
    if not isinstance(source_ref, str) or not source_ref.strip():
        raise UnstructuredGraphValidationError("unstructured FIR record requires source_ref")
    if not isinstance(jurisdiction, str) or not jurisdiction.strip():
        raise UnstructuredGraphValidationError("unstructured FIR record requires jurisdiction")

    return source_ref.strip(), jurisdiction.strip()


def _edge_record_id(
    record: NormalizedRecord,
    rel_type: str,
    from_value: str,
    to_value: str,
) -> str:
    return f"{record['record_id']}:{rel_type}:{from_value}:{to_value}"


def _candidate_extraction_method(candidate: EntityCandidate) -> str:
    method = str(candidate.get("extraction_method") or "").strip().lower()
    if method not in {"regex", "ner"}:
        raise UnstructuredGraphValidationError(
            f"unsupported extraction_method for graph edge: {method or '<missing>'}"
        )
    return method


def _relationship_kwargs(
    record: NormalizedRecord,
    *,
    source_ref: str,
    jurisdiction: str,
    candidate: EntityCandidate,
    result: ResolutionResult,
) -> dict[str, Any]:
    return {
        "source_ref": source_ref,
        "jurisdiction": jurisdiction,
        "extraction_method": _candidate_extraction_method(candidate),
        "confidence": float(result.get("confidence") or candidate.get("confidence") or 0.0),
        "valid_from": None,
        "valid_to": None,
    }


def _append_relationship(
    plan: GraphPlan,
    *,
    record: NormalizedRecord,
    rel_type: str,
    from_label: str,
    from_key: str,
    from_value: str,
    to_label: str,
    to_key: str,
    to_value: str,
    source_ref: str,
    jurisdiction: str,
    candidate: EntityCandidate,
    result: ResolutionResult,
    seen_edge_ids: set[str],
    **properties: Any,
) -> None:
    edge_id = _edge_record_id(record, rel_type, from_value, to_value)
    if edge_id in seen_edge_ids:
        return

    _add_relationship(
        plan,
        rel_type=rel_type,
        from_label=from_label,
        from_key=from_key,
        from_value=from_value,
        to_label=to_label,
        to_key=to_key,
        to_value=to_value,
        record=record,
        **_relationship_kwargs(
            record,
            source_ref=source_ref,
            jurisdiction=jurisdiction,
            candidate=candidate,
            result=result,
        ),
        **properties,
    )

    spec = plan.relationships[-1]
    if spec.record_id != record["record_id"]:
        plan.relationships[-1] = RelationshipSpec(
            rel_type=spec.rel_type,
            from_label=spec.from_label,
            from_key=spec.from_key,
            from_value=spec.from_value,
            to_label=spec.to_label,
            to_key=spec.to_key,
            to_value=spec.to_value,
            record_id=edge_id,
            properties=spec.properties,
        )
        spec = plan.relationships[-1]

    validate_edge_provenance(spec.properties)
    seen_edge_ids.add(edge_id)


def _ensure_fir_anchor(
    plan: GraphPlan,
    record: NormalizedRecord,
    *,
    source_ref: str,
    jurisdiction: str,
    fir_nodes_added: set[str],
) -> None:
    if source_ref in fir_nodes_added:
        return

    _add_node(
        plan,
        LABEL_FIR,
        "fir_id",
        source_ref,
        **provenance(record, source_ref=source_ref, jurisdiction=jurisdiction),
    )
    _canonical_node(
        plan,
        LABEL_CASE,
        "case_no",
        source_ref,
        record,
        fir_no=source_ref,
        status=None,
    )
    _canonical_node(
        plan,
        LABEL_INCIDENT,
        "incident_id",
        f"{source_ref}:incident",
        record,
        case_no=source_ref,
    )
    fir_nodes_added.add(source_ref)


def _map_resolved_identifier(
    plan: GraphPlan,
    *,
    record: NormalizedRecord,
    candidate: EntityCandidate,
    result: ResolutionResult,
    source_ref: str,
    jurisdiction: str,
    registry: CanonicalRegistry,
    fir_nodes_added: set[str],
    seen_edge_ids: set[str],
    involved_persons: set[str],
) -> None:
    entity_type = candidate["entity_type"]
    mapping = _IDENTIFIER_MAPPING.get(entity_type)
    if mapping is None:
        return

    person_id = result.get("matched_entity_id")
    if not person_id:
        return

    legacy_label, legacy_key, normalizer, rel_type, canonical_label, canonical_key = mapping
    identifier_value = normalizer(candidate_normalized_value(candidate))

    _ensure_fir_anchor(
        plan,
        record,
        source_ref=source_ref,
        jurisdiction=jurisdiction,
        fir_nodes_added=fir_nodes_added,
    )
    _add_node(plan, LABEL_PERSON, "person_id", person_id)
    _add_node(
        plan,
        legacy_label,
        legacy_key,
        identifier_value,
        **provenance(record, source_ref=source_ref, jurisdiction=jurisdiction),
    )
    _canonical_node(plan, canonical_label, canonical_key, identifier_value, record)

    rel_kwargs = _relationship_kwargs(
        record,
        source_ref=source_ref,
        jurisdiction=jurisdiction,
        candidate=candidate,
        result=result,
    )
    _append_relationship(
        plan,
        record=record,
        rel_type=rel_type,
        from_label=LABEL_PERSON,
        from_key="person_id",
        from_value=person_id,
        to_label=legacy_label,
        to_key=legacy_key,
        to_value=identifier_value,
        source_ref=source_ref,
        jurisdiction=jurisdiction,
        candidate=candidate,
        result=result,
        seen_edge_ids=seen_edge_ids,
    )
    _append_relationship(
        plan,
        record=record,
        rel_type=REL_INVOLVED_IN,
        from_label=LABEL_PERSON,
        from_key="person_id",
        from_value=person_id,
        to_label=LABEL_FIR,
        to_key="fir_id",
        to_value=source_ref,
        source_ref=source_ref,
        jurisdiction=jurisdiction,
        candidate=candidate,
        result=result,
        seen_edge_ids=seen_edge_ids,
    )

    _canonical_relationship(
        plan,
        rel_type=REL_USES,
        from_label=LABEL_PERSON,
        from_key="person_id",
        from_value=person_id,
        to_label=canonical_label,
        to_key=canonical_key,
        to_value=identifier_value,
        record=record,
        **rel_kwargs,
    )
    if person_id not in involved_persons:
        _canonical_relationship(
            plan,
            rel_type=REL_CO_ACCUSED_IN,
            from_label=LABEL_PERSON,
            from_key="person_id",
            from_value=person_id,
            to_label=LABEL_CASE,
            to_key="case_no",
            to_value=source_ref,
            record=record,
            **rel_kwargs,
        )
        involved_persons.add(person_id)

    last_spec = plan.relationships[-1]
    validate_edge_provenance(last_spec.properties)


def _map_resolved_person_name(
    plan: GraphPlan,
    *,
    record: NormalizedRecord,
    candidate: EntityCandidate,
    result: ResolutionResult,
    source_ref: str,
    jurisdiction: str,
    fir_nodes_added: set[str],
    seen_edge_ids: set[str],
    involved_persons: set[str],
) -> None:
    person_id = result.get("matched_entity_id")
    if not person_id:
        return

    rel_kwargs = _relationship_kwargs(
        record,
        source_ref=source_ref,
        jurisdiction=jurisdiction,
        candidate=candidate,
        result=result,
    )

    _ensure_fir_anchor(
        plan,
        record,
        source_ref=source_ref,
        jurisdiction=jurisdiction,
        fir_nodes_added=fir_nodes_added,
    )
    _add_node(plan, LABEL_PERSON, "person_id", person_id)
    _append_relationship(
        plan,
        record=record,
        rel_type=REL_INVOLVED_IN,
        from_label=LABEL_PERSON,
        from_key="person_id",
        from_value=person_id,
        to_label=LABEL_FIR,
        to_key="fir_id",
        to_value=source_ref,
        source_ref=source_ref,
        jurisdiction=jurisdiction,
        candidate=candidate,
        result=result,
        seen_edge_ids=seen_edge_ids,
    )
    if person_id not in involved_persons:
        _canonical_relationship(
            plan,
            rel_type=REL_CO_ACCUSED_IN,
            from_label=LABEL_PERSON,
            from_key="person_id",
            from_value=person_id,
            to_label=LABEL_CASE,
            to_key="case_no",
            to_value=source_ref,
            record=record,
            **rel_kwargs,
        )
        involved_persons.add(person_id)


def map_resolved_unstructured_fir(
    plan: GraphPlan,
    record: NormalizedRecord,
    resolved_entries: list[tuple[EntityCandidate, ResolutionResult]],
    *,
    registry: CanonicalRegistry | None = None,
) -> None:
    """Project resolved unstructured FIR candidates onto an existing graph plan."""
    _ = registry or build_canonical_registry()
    source_ref, jurisdiction = _require_unstructured_record(record)

    fir_nodes_added: set[str] = set()
    seen_edge_ids: set[str] = set()
    involved_persons: set[str] = set()

    for candidate, result in resolved_entries:
        if result.get("status") != RESOLUTION_STATUS_RESOLVED:
            continue

        entity_type = candidate["entity_type"]
        if entity_type in _IDENTIFIER_MAPPING:
            _map_resolved_identifier(
                plan,
                record=record,
                candidate=candidate,
                result=result,
                source_ref=source_ref,
                jurisdiction=jurisdiction,
                registry=_,
                fir_nodes_added=fir_nodes_added,
                seen_edge_ids=seen_edge_ids,
                involved_persons=involved_persons,
            )
        elif entity_type in {"person", "person_name", "name"}:
            _map_resolved_person_name(
                plan,
                record=record,
                candidate=candidate,
                result=result,
                source_ref=source_ref,
                jurisdiction=jurisdiction,
                fir_nodes_added=fir_nodes_added,
                seen_edge_ids=seen_edge_ids,
                involved_persons=involved_persons,
            )


def build_unstructured_fir_graph_plan(
    record: NormalizedRecord,
    *,
    registry: CanonicalRegistry | None = None,
    include_ner: bool = True,
    queue_reviews: bool = True,
) -> UnstructuredGraphBuildResult:
    """Extract, resolve, and map one unstructured FIR record into a graph plan."""
    source_ref, jurisdiction = _require_unstructured_record(record)
    active_registry = registry or build_canonical_registry()
    candidates = extract_unified_from_unstructured_record(record, include_ner=include_ner)

    plan = GraphPlan()
    resolution_results: list[ResolutionResult] = []
    resolved: list[tuple[EntityCandidate, ResolutionResult]] = []
    skipped: list[tuple[EntityCandidate, ResolutionResult]] = []
    queued_reviews: list[dict[str, Any]] = []

    for candidate in candidates:
        result = resolve_candidate(
            candidate,
            active_registry,
            jurisdiction=jurisdiction,
        )
        resolution_results.append(result)

        if result.get("status") == RESOLUTION_STATUS_RESOLVED:
            resolved.append((candidate, result))
            continue

        skipped.append((candidate, result))
        if queue_reviews and result.get("status") == RESOLUTION_STATUS_AMBIGUOUS:
            review = create_review_from_resolution(
                result=result,
                jurisdiction=jurisdiction,
                candidate=candidate,
            )
            if review is not None:
                queued_reviews.append(review)

    map_resolved_unstructured_fir(
        plan,
        record,
        resolved,
        registry=active_registry,
    )

    for relationship in plan.relationships:
        validate_edge_provenance(relationship.properties)

    return UnstructuredGraphBuildResult(
        plan=plan,
        resolution_results=resolution_results,
        resolved=resolved,
        skipped=skipped,
        queued_reviews=queued_reviews,
    )


def import_unstructured_fir_graph(
    record: NormalizedRecord,
    *,
    dry_run: bool = False,
    registry: CanonicalRegistry | None = None,
    include_ner: bool = True,
    queue_reviews: bool = True,
) -> dict[str, Any]:
    """Build and optionally import the graph projection for one unstructured FIR."""
    build_result = build_unstructured_fir_graph_plan(
        record,
        registry=registry,
        include_ner=include_ner,
        queue_reviews=queue_reviews,
    )
    import_result = import_cnas_graph(plan=build_result.plan, dry_run=dry_run)
    return {
        **import_result,
        "resolved_candidates": len(build_result.resolved),
        "skipped_candidates": len(build_result.skipped),
        "queued_reviews": len(build_result.queued_reviews),
    }
