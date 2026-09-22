"""Business logic for saved CNAS investigations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.investigation_repository import get_repository

REQUIRED_FIELDS = {
    "id",
    "name",
    "description",
    "selected_entity_ids",
    "graph_seeds",
    "from_datetime",
    "to_datetime",
    "created_by",
    "jurisdiction",
    "created_at",
    "updated_at",
}


class InvestigationNotFoundError(Exception):
    pass


class InvestigationValidationError(ValueError):
    pass


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise InvestigationValidationError(f"{field_name} must be a string")
    trimmed = value.strip()
    if not trimmed:
        raise InvestigationValidationError(f"{field_name} is required")
    return trimmed


def _normalize_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvestigationValidationError("description must be a string or null")
    trimmed = value.strip()
    return trimmed or None


def _normalize_optional_datetime(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvestigationValidationError(f"{field_name} must be a string or null")
    trimmed = value.strip()
    return trimmed or None


def _normalize_string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise InvestigationValidationError(f"{field_name} must be an array")
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise InvestigationValidationError(
                f"{field_name}[{index}] must be a string"
            )
        trimmed = item.strip()
        if trimmed:
            normalized.append(trimmed)
    return normalized


def _serialize_record(record: dict[str, Any]) -> dict[str, Any]:
    return {field: record.get(field) for field in sorted(REQUIRED_FIELDS)}


def _validate_create_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise InvestigationValidationError("Request body must be a JSON object")

    return {
        "name": _normalize_string(payload.get("name"), "name"),
        "description": _normalize_optional_string(payload.get("description")),
        "selected_entity_ids": _normalize_string_list(
            payload.get("selected_entity_ids"),
            "selected_entity_ids",
        ),
        "graph_seeds": _normalize_string_list(
            payload.get("graph_seeds"),
            "graph_seeds",
        ),
        "from_datetime": _normalize_optional_datetime(
            payload.get("from_datetime"),
            "from_datetime",
        ),
        "to_datetime": _normalize_optional_datetime(
            payload.get("to_datetime"),
            "to_datetime",
        ),
    }


def list_investigations() -> dict[str, Any]:
    records = [_serialize_record(record) for record in get_repository().list_all()]
    return {"total": len(records), "data": records}


def list_investigations_for_user(user: dict[str, Any]) -> dict[str, Any]:
    from app.services.investigation_authorization import filter_investigations_for_user

    records = filter_investigations_for_user(user, get_repository().list_all())
    serialized = [_serialize_record(record) for record in records]
    return {"total": len(serialized), "data": serialized}


def get_investigation(investigation_id: str) -> dict[str, Any]:
    record = get_repository().get_by_id(investigation_id)
    if record is None:
        raise InvestigationNotFoundError(f"Investigation '{investigation_id}' was not found")
    return _serialize_record(record)


def create_investigation(
    payload: dict[str, Any],
    *,
    created_by: str | None = None,
    jurisdiction: str | None = None,
) -> dict[str, Any]:
    validated = _validate_create_payload(payload)
    now = _utc_now_iso()
    record = {
        "id": str(uuid.uuid4()),
        **validated,
        "created_by": created_by,
        "jurisdiction": jurisdiction,
        "created_at": now,
        "updated_at": now,
    }
    stored = get_repository().insert(record)
    return _serialize_record(stored)


def update_investigation(investigation_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or not payload:
        raise InvestigationValidationError("Request body must be a non-empty JSON object")

    patch: dict[str, Any] = {"updated_at": _utc_now_iso()}

    if "name" in payload:
        patch["name"] = _normalize_string(payload.get("name"), "name")
    if "description" in payload:
        patch["description"] = _normalize_optional_string(payload.get("description"))
    if "selected_entity_ids" in payload:
        patch["selected_entity_ids"] = _normalize_string_list(
            payload.get("selected_entity_ids"),
            "selected_entity_ids",
        )
    if "graph_seeds" in payload:
        patch["graph_seeds"] = _normalize_string_list(
            payload.get("graph_seeds"),
            "graph_seeds",
        )
    if "from_datetime" in payload:
        patch["from_datetime"] = _normalize_optional_datetime(
            payload.get("from_datetime"),
            "from_datetime",
        )
    if "to_datetime" in payload:
        patch["to_datetime"] = _normalize_optional_datetime(
            payload.get("to_datetime"),
            "to_datetime",
        )

    updated = get_repository().update_by_id(investigation_id, patch)
    if updated is None:
        raise InvestigationNotFoundError(f"Investigation '{investigation_id}' was not found")
    return _serialize_record(updated)
