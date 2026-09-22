"""Audit log read service with jurisdiction filtering and safe metadata."""

from __future__ import annotations

from typing import Any

from app.services.audit_repository import get_audit_repository
from app.services.audit_service import sanitize_metadata
from app.services.investigation_authorization import is_admin, user_jurisdictions
from app.services.user_repository import get_user_repository


def _serialize_event(record: dict[str, Any]) -> dict[str, Any]:
    actor_id = record.get("user_id")
    actor_username = None
    if actor_id:
        user = get_user_repository().get_by_id(str(actor_id))
        if user is not None:
            actor_username = user.get("username")

    return {
        "id": record["id"],
        "timestamp": record["timestamp"],
        "actor_id": actor_id,
        "actor_username": actor_username,
        "action": record["action"],
        "resource_type": record["resource_type"],
        "resource_id": record.get("resource_id"),
        "jurisdiction": record.get("jurisdiction"),
        "result": record["result"],
        "metadata": sanitize_metadata(record.get("metadata")),
    }


def list_audit_logs_for_user(
    user: dict[str, Any],
    *,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    events = get_audit_repository().list_events(limit=limit, offset=offset)
    if is_admin(user):
        serialized = [_serialize_event(event) for event in events]
        return {"total": len(serialized), "events": serialized}

    allowed = set(user_jurisdictions(user))
    filtered = [
        event
        for event in events
        if event.get("jurisdiction") in allowed or event.get("jurisdiction") is None
    ]
    serialized = [_serialize_event(event) for event in filtered]
    return {"total": len(serialized), "events": serialized}
