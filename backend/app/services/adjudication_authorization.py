"""Jurisdiction and role checks for entity adjudication workflows."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.services.audit_service import AuditWriteError, audit_adjudication_read
from app.services.investigation_authorization import is_admin, user_jurisdictions


def can_read_review(user: dict[str, Any], review: dict[str, Any]) -> bool:
    if is_admin(user):
        return True
    jurisdiction = review.get("jurisdiction")
    if jurisdiction is None:
        return False
    return jurisdiction in user_jurisdictions(user)


def filter_reviews_for_user(
    user: dict[str, Any],
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if is_admin(user):
        return records
    allowed = set(user_jurisdictions(user))
    return [record for record in records if record.get("jurisdiction") in allowed]


def authorize_review_read(user: dict[str, Any], review: dict[str, Any]) -> None:
    if can_read_review(user, review):
        return

    try:
        audit_adjudication_read(
            user,
            review_id=str(review.get("id")),
            jurisdiction=review.get("jurisdiction"),
            result="denied",
        )
    except AuditWriteError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit logging unavailable",
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions",
    )


def authorize_review_decision(user: dict[str, Any], review: dict[str, Any]) -> None:
    authorize_review_read(user, review)

    if is_admin(user):
        return

    if user.get("role") != "ANALYST":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
