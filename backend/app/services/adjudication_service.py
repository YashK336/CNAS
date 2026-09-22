"""Human adjudication workflow for ambiguous entity resolution matches."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.adjudication_authorization import (
    authorize_review_decision,
    authorize_review_read,
    filter_reviews_for_user,
)
from app.services.entity_resolution import (
    CanonicalRegistry,
    ResolutionResult,
    build_canonical_registry,
    resolve_candidate,
)
from app.services.extraction import EntityCandidate
from app.services.import_overlay import append_overlay_rows
from app.services.resolution_config import (
    IDENTIFIER_ENTITY_TYPES,
    MAPPING_SOURCE_ADJUDICATION,
    NAME_ENTITY_TYPES,
    RESOLUTION_STATUS_AMBIGUOUS,
)
from app.services.review_repository import get_review_repository


class AdjudicationValidationError(ValueError):
    """Raised when adjudication payloads are malformed."""


class ReviewNotFoundError(LookupError):
    """Raised when a review record does not exist."""


class ReviewStateError(RuntimeError):
    """Raised when a review is not in a valid state for the requested action."""


REVIEW_STATUS_PENDING = "pending"
REVIEW_STATUS_CONFIRMED = "confirmed"
REVIEW_STATUS_REJECTED = "rejected"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def compute_review_fingerprint(
    *,
    candidate_value: str,
    entity_type: str,
    proposed_entity_ids: list[str],
    matching_method: str,
    jurisdiction: str | None,
) -> str:
    normalized_value = candidate_value.strip().lower()
    sorted_ids = sorted(str(item) for item in proposed_entity_ids)
    payload = "|".join(
        [
            entity_type.strip().lower(),
            normalized_value,
            matching_method.strip().lower(),
            (jurisdiction or "").strip().upper(),
            ",".join(sorted_ids),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_candidate_rejected(
    *,
    candidate_value: str,
    entity_type: str,
    proposed_entity_ids: list[str],
    matching_method: str,
    jurisdiction: str | None,
) -> bool:
    fingerprint = compute_review_fingerprint(
        candidate_value=candidate_value,
        entity_type=entity_type,
        proposed_entity_ids=proposed_entity_ids,
        matching_method=matching_method,
        jurisdiction=jurisdiction,
    )
    return get_review_repository().is_rejected(fingerprint)


def _build_corroborating_evidence(
    candidate: EntityCandidate,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "source": candidate.get("source"),
        "record_id": candidate.get("record_id"),
        "extraction_method": candidate.get("extraction_method"),
        "source_text": candidate.get("source_text"),
        "confidence": candidate.get("confidence"),
    }
    if extra:
        evidence.update(extra)
    return {key: value for key, value in evidence.items() if value is not None}


def _serialize_review(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_id": record["id"],
        "candidate_value": record["candidate_value"],
        "entity_type": record["entity_type"],
        "reference_entity_id": record.get("reference_entity_id"),
        "proposed_entity_ids": list(record.get("proposed_entity_ids") or []),
        "matching_method": record["matching_method"],
        "match_score": record.get("match_score"),
        "candidate_scores": dict(record.get("candidate_scores") or {}),
        "corroborating_evidence": dict(record.get("corroborating_evidence") or {}),
        "ambiguity_reason": record["ambiguity_reason"],
        "jurisdiction": record.get("jurisdiction"),
        "status": record["status"],
        "reviewer_id": record.get("reviewer_id"),
        "reviewed_at": record.get("reviewed_at"),
        "decision_reason": record.get("decision_reason"),
        "confirmed_entity_id": record.get("confirmed_entity_id"),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }


def create_review_from_resolution(
    *,
    result: ResolutionResult,
    jurisdiction: str | None,
    candidate: EntityCandidate | None = None,
    reference_entity_id: str | None = None,
) -> dict[str, Any] | None:
    """Persist a pending review for an ambiguous resolution result."""
    if result.get("status") != RESOLUTION_STATUS_AMBIGUOUS:
        return None

    proposed_entity_ids = list(result.get("proposed_entity_ids") or [])
    if not proposed_entity_ids:
        raise AdjudicationValidationError(
            "ambiguous resolution must include proposed_entity_ids"
        )

    matching_method = str(result.get("method") or "")
    fingerprint = compute_review_fingerprint(
        candidate_value=result["candidate_value"],
        entity_type=result["entity_type"],
        proposed_entity_ids=proposed_entity_ids,
        matching_method=matching_method,
        jurisdiction=jurisdiction,
    )

    repository = get_review_repository()
    if repository.is_rejected(fingerprint):
        return None

    existing = repository.get_by_fingerprint(fingerprint)
    if existing is not None:
        if existing["status"] == REVIEW_STATUS_PENDING:
            return _serialize_review(existing)
        return None

    now = _utc_now_iso()
    candidate_scores = dict(result.get("candidate_scores") or {})
    match_score = result.get("confidence")
    if match_score is None and candidate_scores:
        match_score = max(candidate_scores.values())

    evidence = dict(result.get("corroborating_evidence") or {})
    if candidate is not None:
        evidence = _build_corroborating_evidence(candidate, evidence)

    record = {
        "id": str(uuid.uuid4()),
        "candidate_value": result["candidate_value"],
        "entity_type": result["entity_type"],
        "reference_entity_id": reference_entity_id,
        "proposed_entity_ids": proposed_entity_ids,
        "matching_method": matching_method,
        "match_score": match_score,
        "candidate_scores": candidate_scores,
        "corroborating_evidence": evidence,
        "ambiguity_reason": str(
            result.get("ambiguity_reason")
            or "Multiple canonical entities matched the extracted candidate."
        ),
        "jurisdiction": jurisdiction,
        "status": REVIEW_STATUS_PENDING,
        "reviewer_id": None,
        "reviewed_at": None,
        "decision_reason": None,
        "confirmed_entity_id": None,
        "fingerprint": fingerprint,
        "created_at": now,
        "updated_at": now,
    }
    stored = repository.insert(record)
    return _serialize_review(stored)


def queue_ambiguous_reviews(
    candidates: list[EntityCandidate],
    *,
    jurisdiction: str | None,
    registry: CanonicalRegistry | None = None,
) -> tuple[list[ResolutionResult], list[dict[str, Any]]]:
    """Resolve candidates and queue persistent reviews for ambiguous matches."""
    active_registry = registry or build_canonical_registry()
    results: list[ResolutionResult] = []
    queued: list[dict[str, Any]] = []

    for candidate in candidates:
        result = resolve_candidate(candidate, active_registry, jurisdiction=jurisdiction)
        results.append(result)
        if result.get("status") != RESOLUTION_STATUS_AMBIGUOUS:
            continue
        review = create_review_from_resolution(
            result=result,
            jurisdiction=jurisdiction,
            candidate=candidate,
        )
        if review is not None:
            queued.append(review)

    return results, queued


def list_pending_reviews(user: dict[str, Any]) -> dict[str, Any]:
    records = filter_reviews_for_user(user, get_review_repository().list_pending())
    serialized = [_serialize_review(record) for record in records]
    return {"total": len(serialized), "reviews": serialized}


def get_review(review_id: str, user: dict[str, Any]) -> dict[str, Any]:
    record = get_review_repository().get_by_id(review_id)
    if record is None:
        raise ReviewNotFoundError(f"Review not found: {review_id}")
    authorize_review_read(user, record)
    return _serialize_review(record)


def _validate_decision_reason(reason: Any) -> str | None:
    if reason is None:
        return None
    if not isinstance(reason, str):
        raise AdjudicationValidationError("reason must be a string")
    trimmed = reason.strip()
    return trimmed or None


def mapping_entity_type_for_review(entity_type: str) -> str:
    kind = str(entity_type or "").strip().lower()
    if kind in NAME_ENTITY_TYPES:
        return "person_name"
    return kind


def apply_confirmed_canonical_mapping(
    review: dict[str, Any],
    canonical_entity_id: str,
    *,
    confirmed_at: str | None = None,
) -> dict[str, Any]:
    """Write the confirmed mention onto overlay entity_mapping."""
    row = {
        "entity_id": canonical_entity_id,
        "entity_type": mapping_entity_type_for_review(str(review.get("entity_type") or "")),
        "source": MAPPING_SOURCE_ADJUDICATION,
        "source_id": review["candidate_value"],
        "_review_id": review.get("id") or review.get("review_id"),
        "_confirmed_at": confirmed_at or _utc_now_iso(),
        "_jurisdiction": review.get("jurisdiction"),
    }
    append_overlay_rows("entity_mapping", [row])
    return row


def _apply_confirmed_mapping_to_graph(
    review: dict[str, Any],
    canonical_entity_id: str,
) -> dict[str, Any] | None:
    """Best-effort: project the confirmed mapping through the existing graph mapper."""
    entity_type = mapping_entity_type_for_review(str(review.get("entity_type") or ""))
    if entity_type not in IDENTIFIER_ENTITY_TYPES:
        return None
    try:
        import pandas as pd

        from app.services.graph.importer import import_cnas_graph
        from app.services.graph.mapper import map_entity_mapping_records
        from app.services.normalization import normalize_row

        payload = {
            "entity_id": canonical_entity_id,
            "entity_type": entity_type,
            "source": MAPPING_SOURCE_ADJUDICATION,
            "source_id": review["candidate_value"],
        }
        record = normalize_row("entity_mapping", pd.Series(payload), 0)
        plan = map_entity_mapping_records([record])
        if not plan.nodes and not plan.relationships:
            return None
        return import_cnas_graph(plan=plan, dry_run=False)
    except Exception:  # noqa: BLE001 - confirmation already persisted in overlay
        return None


def confirm_review(
    review_id: str,
    user: dict[str, Any],
    *,
    canonical_entity_id: str,
    reason: str | None = None,
) -> dict[str, Any]:
    if not isinstance(canonical_entity_id, str) or not canonical_entity_id.strip():
        raise AdjudicationValidationError("canonical_entity_id is required")

    record = get_review_repository().get_by_id(review_id)
    if record is None:
        raise ReviewNotFoundError(f"Review not found: {review_id}")

    authorize_review_decision(user, record)

    if record["status"] != REVIEW_STATUS_PENDING:
        raise ReviewStateError("Only pending reviews can be confirmed")

    selected = canonical_entity_id.strip()
    proposed = set(record.get("proposed_entity_ids") or [])
    if selected not in proposed:
        raise AdjudicationValidationError(
            "canonical_entity_id must be one of the proposed canonical IDs"
        )

    now = _utc_now_iso()
    updated = get_review_repository().update_decision(
        review_id,
        {
            "status": REVIEW_STATUS_CONFIRMED,
            "reviewer_id": user.get("id"),
            "reviewed_at": now,
            "decision_reason": _validate_decision_reason(reason),
            "confirmed_entity_id": selected,
            "updated_at": now,
        },
    )
    apply_confirmed_canonical_mapping(updated, selected, confirmed_at=now)
    _apply_confirmed_mapping_to_graph(updated, selected)
    return _serialize_review(updated)


def reject_review(
    review_id: str,
    user: dict[str, Any],
    *,
    reason: str | None = None,
) -> dict[str, Any]:
    record = get_review_repository().get_by_id(review_id)
    if record is None:
        raise ReviewNotFoundError(f"Review not found: {review_id}")

    authorize_review_decision(user, record)

    if record["status"] != REVIEW_STATUS_PENDING:
        raise ReviewStateError("Only pending reviews can be rejected")

    now = _utc_now_iso()
    updated = get_review_repository().update_decision(
        review_id,
        {
            "status": REVIEW_STATUS_REJECTED,
            "reviewer_id": user.get("id"),
            "reviewed_at": now,
            "decision_reason": _validate_decision_reason(reason),
            "confirmed_entity_id": None,
            "updated_at": now,
        },
    )
    get_review_repository().register_rejection(
        fingerprint=updated["fingerprint"],
        review_id=updated["id"],
        reviewer_id=str(user.get("id")) if user.get("id") else None,
        rejected_at=now,
    )
    return _serialize_review(updated)
