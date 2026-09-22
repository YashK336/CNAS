from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.core.security import authorize_roles, get_current_user
from app.services.adjudication_service import (
    AdjudicationValidationError,
    ReviewNotFoundError,
    ReviewStateError,
    confirm_review,
    get_review,
    list_pending_reviews,
    queue_ambiguous_reviews,
    reject_review,
)
from app.services.audit_service import (
    AuditWriteError,
    audit_adjudication_confirm,
    audit_adjudication_reject,
)
from app.services.extraction import EntityCandidate

router = APIRouter(
    prefix="/adjudication",
    tags=["Adjudication"],
)

READ_ROLES = ("ADMIN", "ANALYST", "VIEWER")
WRITE_ROLES = ("ADMIN", "ANALYST")

REQUIRED_CANDIDATE_FIELDS = (
    "entity_type",
    "value",
    "confidence",
    "source",
    "record_id",
    "start",
    "end",
    "offset",
    "source_text",
    "extraction_method",
    "resolution_eligible",
)


def _raise_audit_unavailable(exc: AuditWriteError) -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Audit logging unavailable",
    ) from exc


def _parse_candidate(item: dict[str, Any], index: int) -> EntityCandidate:
    missing = [field for field in REQUIRED_CANDIDATE_FIELDS if field not in item]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"candidates[{index}] missing required fields: {', '.join(missing)}",
        )
    if not isinstance(item.get("entity_type"), str) or not item["entity_type"].strip():
        raise HTTPException(
            status_code=422,
            detail=f"candidates[{index}].entity_type must be a string",
        )
    if not isinstance(item.get("value"), str):
        raise HTTPException(status_code=422, detail=f"candidates[{index}].value must be a string")
    return EntityCandidate(**item)


@router.get("/reviews")
@router.get("/reviews/")
def get_pending_reviews(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *READ_ROLES,
        resource_type="entity_resolution_review",
    )
    return list_pending_reviews(current_user)


@router.get("/reviews/{review_id}")
def get_review_by_id(
    review_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *READ_ROLES,
        resource_type="entity_resolution_review",
        resource_id=review_id,
    )
    try:
        return get_review(review_id, current_user)
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except AuditWriteError as exc:
        _raise_audit_unavailable(exc)


@router.post("/reviews/{review_id}/confirm")
def post_confirm_review(
    review_id: str,
    payload: dict[str, Any] = Body(...),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *WRITE_ROLES,
        resource_type="entity_resolution_review",
        resource_id=review_id,
    )
    try:
        review = confirm_review(
            review_id,
            current_user,
            canonical_entity_id=str(payload.get("canonical_entity_id") or ""),
            reason=payload.get("reason"),
        )
        audit_adjudication_confirm(
            current_user,
            review_id=review_id,
            jurisdiction=review.get("jurisdiction"),
            result="success",
            metadata={
                "confirmed_entity_id": review.get("confirmed_entity_id"),
                "decision_reason": review.get("decision_reason"),
            },
        )
        return review
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReviewStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AdjudicationValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            try:
                audit_adjudication_confirm(
                    current_user,
                    review_id=review_id,
                    jurisdiction=None,
                    result="denied",
                )
            except AuditWriteError as audit_exc:
                _raise_audit_unavailable(audit_exc)
        raise
    except AuditWriteError as exc:
        _raise_audit_unavailable(exc)


@router.post("/reviews/{review_id}/reject")
def post_reject_review(
    review_id: str,
    payload: dict[str, Any] = Body(default_factory=dict),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *WRITE_ROLES,
        resource_type="entity_resolution_review",
        resource_id=review_id,
    )
    try:
        review = reject_review(
            review_id,
            current_user,
            reason=payload.get("reason"),
        )
        audit_adjudication_reject(
            current_user,
            review_id=review_id,
            jurisdiction=review.get("jurisdiction"),
            result="success",
            metadata={"decision_reason": review.get("decision_reason")},
        )
        return review
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReviewStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AdjudicationValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            try:
                audit_adjudication_reject(
                    current_user,
                    review_id=review_id,
                    jurisdiction=None,
                    result="denied",
                )
            except AuditWriteError as audit_exc:
                _raise_audit_unavailable(audit_exc)
        raise
    except AuditWriteError as exc:
        _raise_audit_unavailable(exc)


@router.post("/evaluate")
def post_evaluate_candidates(
    payload: dict[str, Any] = Body(...),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Resolve candidates and queue persistent reviews for ambiguous matches."""
    authorize_roles(
        current_user,
        *WRITE_ROLES,
        resource_type="entity_resolution_review",
    )

    raw_candidates = payload.get("candidates")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise HTTPException(status_code=422, detail="candidates must be a non-empty array")

    jurisdiction = payload.get("jurisdiction")
    if jurisdiction is not None and not isinstance(jurisdiction, str):
        raise HTTPException(status_code=422, detail="jurisdiction must be a string")

    candidates: list[EntityCandidate] = []
    for index, item in enumerate(raw_candidates):
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=422,
                detail=f"candidates[{index}] must be an object",
            )
        candidates.append(_parse_candidate(item, index))

    try:
        results, queued = queue_ambiguous_reviews(
            candidates,
            jurisdiction=jurisdiction.strip() if isinstance(jurisdiction, str) else None,
        )
        return {
            "resolution_results": results,
            "queued_reviews": queued,
            "queued_total": len(queued),
        }
    except AdjudicationValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
