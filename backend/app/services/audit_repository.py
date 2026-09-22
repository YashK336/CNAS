"""Append-only PostgreSQL repository for CNAS audit logs."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.core.database import get_cursor

AUDIT_LOGS_TABLE = "audit_logs"
VALID_RESULTS = ("success", "denied", "failure")

AUDIT_SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS {AUDIT_LOGS_TABLE} (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    user_id UUID,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    jurisdiction TEXT,
    result TEXT NOT NULL CHECK (result IN ('success', 'denied', 'failure')),
    metadata JSONB NOT NULL DEFAULT '{{}}'
);
"""

INSERT_AUDIT_SQL = f"""
INSERT INTO {AUDIT_LOGS_TABLE} (
    id,
    timestamp,
    user_id,
    action,
    resource_type,
    resource_id,
    jurisdiction,
    result,
    metadata
) VALUES (
    %(id)s,
    %(timestamp)s,
    %(user_id)s,
    %(action)s,
    %(resource_type)s,
    %(resource_id)s,
    %(jurisdiction)s,
    %(result)s,
    %(metadata)s
)
"""

LIST_AUDIT_SQL = f"""
SELECT
    id,
    timestamp,
    user_id,
    action,
    resource_type,
    resource_id,
    jurisdiction,
    result,
    metadata
FROM {AUDIT_LOGS_TABLE}
ORDER BY timestamp DESC
LIMIT %(limit)s OFFSET %(offset)s
"""


class AuditRepository(Protocol):
    def ensure_schema(self) -> None: ...

    def append(self, record: dict[str, Any]) -> dict[str, Any]: ...

    def list_events(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]: ...


_repository: AuditRepository | None = None


def set_repository(repository: AuditRepository | None) -> None:
    global _repository
    _repository = repository


def get_audit_repository() -> AuditRepository:
    global _repository
    if _repository is None:
        from app.core.config import postgres_configured, use_memory_store

        if postgres_configured() and not use_memory_store():
            _repository = PostgresAuditRepository()
        else:
            _repository = InMemoryAuditRepository()
    return _repository


def _format_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    return str(value)


def _normalize_result(result: str) -> str:
    normalized = str(result).strip().lower()
    if normalized not in VALID_RESULTS:
        raise ValueError(f"result must be one of {', '.join(VALID_RESULTS)}")
    return normalized


def _normalize_metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("metadata must be a JSON object")
    return value


def _normalize_record(row: dict[str, Any]) -> dict[str, Any]:
    metadata = row.get("metadata")
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    return {
        "id": str(row["id"]),
        "timestamp": _format_timestamp(row["timestamp"]),
        "user_id": str(row["user_id"]) if row.get("user_id") else None,
        "action": row["action"],
        "resource_type": row["resource_type"],
        "resource_id": row.get("resource_id"),
        "jurisdiction": row.get("jurisdiction"),
        "result": row["result"],
        "metadata": _normalize_metadata(metadata),
    }


def _parse_uuid(value: str) -> UUID:
    return UUID(str(value))


class PostgresAuditRepository:
    def ensure_schema(self) -> None:
        with get_cursor() as cursor:
            cursor.execute(AUDIT_SCHEMA_SQL)

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "id": _parse_uuid(record["id"]),
            "timestamp": record["timestamp"],
            "user_id": _parse_uuid(record["user_id"]) if record.get("user_id") else None,
            "action": record["action"],
            "resource_type": record["resource_type"],
            "resource_id": record.get("resource_id"),
            "jurisdiction": record.get("jurisdiction"),
            "result": _normalize_result(record["result"]),
            "metadata": json.dumps(_normalize_metadata(record.get("metadata"))),
        }
        with get_cursor() as cursor:
            cursor.execute(INSERT_AUDIT_SQL, payload)
        return dict(record)

    def list_events(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        with get_cursor() as cursor:
            cursor.execute(
                LIST_AUDIT_SQL,
                {"limit": max(1, min(limit, 500)), "offset": max(0, offset)},
            )
            rows = cursor.fetchall()
            return [_normalize_record(row) for row in rows]


class InMemoryAuditRepository:
    """Lightweight append-only repository used by unit tests."""

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []

    def ensure_schema(self) -> None:
        return None

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        stored = dict(record)
        self._records.append(stored)
        return dict(stored)

    def list_events(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        bounded_limit = max(1, min(limit, 500))
        bounded_offset = max(0, offset)
        end = len(self._records) - bounded_offset
        if end <= 0:
            return []
        start = max(0, end - bounded_limit)
        window = self._records[start:end]
        return [dict(record) for record in reversed(window)]

    def list_all(self) -> list[dict[str, Any]]:
        return [dict(record) for record in self._records]


def initialize_audit_store() -> None:
    from app.core.config import postgres_configured

    if not postgres_configured():
        return

    repository = get_audit_repository()
    repository.ensure_schema()
