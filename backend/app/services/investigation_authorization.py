"""Jurisdiction and investigation access authorization."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.services.audit_service import AuditWriteError, audit_investigation_create, audit_investigation_update
from app.services.audit_service import audit_investigation_read as audit_investigation_read_event
from app.services.investigations import InvestigationValidationError


def user_jurisdictions(user: dict[str, Any]) -> list[str]:
    return list(user.get("jurisdictions") or [])


def is_admin(user: dict[str, Any]) -> bool:
    return user.get("role") == "ADMIN"


def _normalize_jurisdiction(value: Any) -> str:
    if not isinstance(value, str):
        raise InvestigationValidationError("jurisdiction must be a string")
    normalized = value.strip()
    if not normalized:
        raise InvestigationValidationError("jurisdiction is required")
    return normalized


def _raise_audit_unavailable(exc: AuditWriteError) -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Audit logging unavailable",
    ) from exc


def can_read_investigation(user: dict[str, Any], investigation: dict[str, Any]) -> bool:
    if is_admin(user):
        return True
    jurisdiction = investigation.get("jurisdiction")
    if jurisdiction is None:
        return False
    return jurisdiction in user_jurisdictions(user)


def filter_investigations_for_user(
    user: dict[str, Any],
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if is_admin(user):
        return records
    allowed = set(user_jurisdictions(user))
    return [record for record in records if record.get("jurisdiction") in allowed]


def authorize_investigation_read(
    user: dict[str, Any],
    investigation: dict[str, Any],
) -> None:
    if can_read_investigation(user, investigation):
        return

    try:
        audit_investigation_read_event(
            user,
            investigation_id=str(investigation.get("id")),
            jurisdiction=investigation.get("jurisdiction"),
            result="denied",
        )
    except AuditWriteError as exc:
        _raise_audit_unavailable(exc)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions",
    )


def authorize_investigation_update(
    user: dict[str, Any],
    investigation: dict[str, Any],
) -> None:
    if not can_read_investigation(user, investigation):
        try:
            audit_investigation_read_event(
                user,
                investigation_id=str(investigation.get("id")),
                jurisdiction=investigation.get("jurisdiction"),
                result="denied",
            )
        except AuditWriteError as exc:
            _raise_audit_unavailable(exc)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    if is_admin(user):
        return

    owner_id = investigation.get("created_by")
    if owner_id is None or str(owner_id) != str(user.get("id")):
        try:
            audit_investigation_update(
                user,
                investigation_id=str(investigation.get("id")),
                jurisdiction=investigation.get("jurisdiction"),
                result="denied",
            )
        except AuditWriteError as exc:
            _raise_audit_unavailable(exc)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


def resolve_create_jurisdiction(
    user: dict[str, Any],
    payload: dict[str, Any],
) -> str:
    """Resolve jurisdiction for a new investigation."""
    explicit = payload.get("jurisdiction")
    assigned = user_jurisdictions(user)

    if is_admin(user):
        if explicit is None:
            raise InvestigationValidationError(
                "jurisdiction is required when creating an investigation"
            )
        return _normalize_jurisdiction(explicit)

    if explicit is not None:
        selected = _normalize_jurisdiction(explicit)
        if selected not in assigned:
            try:
                audit_investigation_create(
                    user,
                    investigation_id=None,
                    jurisdiction=selected,
                    result="denied",
                )
            except AuditWriteError as exc:
                _raise_audit_unavailable(exc)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return selected

    if len(assigned) == 1:
        return assigned[0]

    if not assigned:
        raise InvestigationValidationError(
            "user has no assigned jurisdictions for investigation creation"
        )

    raise InvestigationValidationError(
        "jurisdiction is required when the user has multiple assignments"
    )
