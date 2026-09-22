"""Append-only audit logging for security-sensitive CNAS operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.audit_repository import get_audit_repository

SENSITIVE_METADATA_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "access_token",
        "token",
        "jwt",
        "secret",
        "authorization",
        "credentials",
        "bearer",
    }
)


class AuditWriteError(Exception):
    """Raised when a required audit event cannot be persisted."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}

    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        normalized_key = str(key).strip().lower()
        if normalized_key in SENSITIVE_METADATA_KEYS:
            continue
        if isinstance(value, dict):
            nested = sanitize_metadata(value)
            if nested:
                sanitized[key] = nested
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_metadata(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


def record_audit_event(
    *,
    user_id: str | None,
    action: str,
    resource_type: str,
    result: str,
    resource_id: str | None = None,
    jurisdiction: str | None = None,
    metadata: dict[str, Any] | None = None,
    required: bool = True,
) -> dict[str, Any]:
    """Persist an append-only audit event.

    When ``required`` is True, audit persistence failures propagate as
    ``AuditWriteError`` so security-sensitive operations are not completed
    without an audit trail.
    """
    record = {
        "id": str(uuid.uuid4()),
        "timestamp": _utc_now_iso(),
        "user_id": str(user_id) if user_id else None,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "jurisdiction": jurisdiction,
        "result": result,
        "metadata": sanitize_metadata(metadata),
    }

    try:
        return get_audit_repository().append(record)
    except Exception as exc:
        if required:
            raise AuditWriteError("Failed to persist audit event") from exc
        return record


def audit_auth_login_success(user: dict[str, Any]) -> dict[str, Any]:
    return record_audit_event(
        user_id=user["id"],
        action="auth.login.success",
        resource_type="user",
        resource_id=str(user["id"]),
        result="success",
        metadata={"username": user.get("username"), "role": user.get("role")},
    )


def audit_auth_login_failure(*, username: str | None = None) -> dict[str, Any]:
    return record_audit_event(
        user_id=None,
        action="auth.login.failure",
        resource_type="user",
        result="failure",
        metadata={"username": username},
    )


def audit_auth_unauthenticated(*, reason: str) -> dict[str, Any]:
    return record_audit_event(
        user_id=None,
        action="auth.access.unauthenticated",
        resource_type="auth",
        result="denied",
        metadata={"reason": reason},
    )


def audit_authorization_role_denied(
    user: dict[str, Any],
    *,
    allowed_roles: tuple[str, ...],
    resource_type: str,
    resource_id: str | None = None,
) -> dict[str, Any]:
    return record_audit_event(
        user_id=user.get("id"),
        action="authorization.role.denied",
        resource_type=resource_type,
        resource_id=resource_id,
        result="denied",
        metadata={
            "role": user.get("role"),
            "allowed_roles": list(allowed_roles),
        },
    )


def audit_investigation_list_success(user: dict[str, Any], *, total: int) -> dict[str, Any]:
    return record_audit_event(
        user_id=user.get("id"),
        action="investigation.list",
        resource_type="investigation",
        result="success",
        metadata={"total": total},
    )


def audit_investigation_read(
    user: dict[str, Any] | None,
    *,
    investigation_id: str,
    jurisdiction: str | None,
    result: str,
) -> dict[str, Any]:
    return record_audit_event(
        user_id=user.get("id") if user else None,
        action="investigation.read",
        resource_type="investigation",
        resource_id=investigation_id,
        jurisdiction=jurisdiction,
        result=result,
    )


def audit_investigation_create(
    user: dict[str, Any],
    *,
    investigation_id: str | None,
    jurisdiction: str | None,
    result: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return record_audit_event(
        user_id=user.get("id"),
        action="investigation.create",
        resource_type="investigation",
        resource_id=investigation_id,
        jurisdiction=jurisdiction,
        result=result,
        metadata=metadata,
    )


def audit_investigation_update(
    user: dict[str, Any],
    *,
    investigation_id: str,
    jurisdiction: str | None,
    result: str,
) -> dict[str, Any]:
    return record_audit_event(
        user_id=user.get("id"),
        action="investigation.update",
        resource_type="investigation",
        resource_id=investigation_id,
        jurisdiction=jurisdiction,
        result=result,
    )


def audit_investigation_report(
    user: dict[str, Any],
    *,
    investigation_id: str | None,
    jurisdiction: str | None,
    result: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return record_audit_event(
        user_id=user.get("id"),
        action="investigation.report.export",
        resource_type="investigation_report",
        resource_id=investigation_id,
        jurisdiction=jurisdiction,
        result=result,
        metadata=metadata,
    )


def audit_case_report(
    user: dict[str, Any],
    *,
    fir_id: str,
    result: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return record_audit_event(
        user_id=user.get("id"),
        action="case.report.export",
        resource_type="investigation_report",
        resource_id=fir_id,
        result=result,
        metadata=metadata,
    )


def audit_adjudication_list(user: dict[str, Any], *, total: int) -> dict[str, Any]:
    return record_audit_event(
        user_id=user.get("id"),
        action="adjudication.review.list",
        resource_type="entity_resolution_review",
        result="success",
        metadata={"total": total},
    )


def audit_adjudication_read(
    user: dict[str, Any] | None,
    *,
    review_id: str,
    jurisdiction: str | None,
    result: str,
) -> dict[str, Any]:
    return record_audit_event(
        user_id=user.get("id") if user else None,
        action="adjudication.review.read",
        resource_type="entity_resolution_review",
        resource_id=review_id,
        jurisdiction=jurisdiction,
        result=result,
    )


def audit_adjudication_confirm(
    user: dict[str, Any],
    *,
    review_id: str,
    jurisdiction: str | None,
    result: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return record_audit_event(
        user_id=user.get("id"),
        action="adjudication.review.confirm",
        resource_type="entity_resolution_review",
        resource_id=review_id,
        jurisdiction=jurisdiction,
        result=result,
        metadata=metadata,
    )


def audit_adjudication_reject(
    user: dict[str, Any],
    *,
    review_id: str,
    jurisdiction: str | None,
    result: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return record_audit_event(
        user_id=user.get("id"),
        action="adjudication.review.reject",
        resource_type="entity_resolution_review",
        resource_id=review_id,
        jurisdiction=jurisdiction,
        result=result,
        metadata=metadata,
    )


def audit_log_list(user: dict[str, Any], *, total: int) -> dict[str, Any]:
    return record_audit_event(
        user_id=user.get("id"),
        action="audit.log.list",
        resource_type="audit_log",
        result="success",
        metadata={"total": total},
    )


def audit_import_inspect(
    user: dict[str, Any],
    *,
    import_id: str | None,
    result: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return record_audit_event(
        user_id=user.get("id"),
        action="data_import.inspect",
        resource_type="data_import",
        resource_id=import_id,
        result=result,
        metadata=metadata,
    )


def audit_import_confirm(
    user: dict[str, Any],
    *,
    import_id: str,
    result: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return record_audit_event(
        user_id=user.get("id"),
        action="data_import.confirm",
        resource_type="data_import",
        resource_id=import_id,
        result=result,
        metadata=metadata,
    )


def audit_import_read(
    user: dict[str, Any],
    *,
    import_id: str | None,
    result: str,
) -> dict[str, Any]:
    return record_audit_event(
        user_id=user.get("id"),
        action="data_import.read",
        resource_type="data_import",
        resource_id=import_id,
        result=result,
    )
