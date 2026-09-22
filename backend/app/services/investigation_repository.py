"""PostgreSQL repository for saved CNAS investigations."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from app.core.database import get_cursor

BASE_DIR = Path(__file__).resolve().parent.parent
LEGACY_JSON_PATH = BASE_DIR / "data" / "investigations.json"

INVESTIGATIONS_TABLE = "investigations"

INVESTIGATIONS_MIGRATION_SQL = (
    f"ALTER TABLE {INVESTIGATIONS_TABLE} "
    "ADD COLUMN IF NOT EXISTS created_by UUID;"
)

INVESTIGATIONS_JURISDICTION_MIGRATION_SQL = (
    f"ALTER TABLE {INVESTIGATIONS_TABLE} "
    "ADD COLUMN IF NOT EXISTS jurisdiction TEXT;"
)

SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS {INVESTIGATIONS_TABLE} (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    selected_entity_ids TEXT[] NOT NULL DEFAULT '{{}}',
    graph_seeds TEXT[] NOT NULL DEFAULT '{{}}',
    from_datetime TEXT,
    to_datetime TEXT,
    created_by UUID,
    jurisdiction TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
"""

INSERT_SQL = f"""
INSERT INTO {INVESTIGATIONS_TABLE} (
    id,
    name,
    description,
    selected_entity_ids,
    graph_seeds,
    from_datetime,
    to_datetime,
    created_by,
    jurisdiction,
    created_at,
    updated_at
) VALUES (
    %(id)s,
    %(name)s,
    %(description)s,
    %(selected_entity_ids)s,
    %(graph_seeds)s,
    %(from_datetime)s,
    %(to_datetime)s,
    %(created_by)s,
    %(jurisdiction)s,
    %(created_at)s,
    %(updated_at)s
)
"""

LIST_SQL = f"""
SELECT
    id,
    name,
    description,
    selected_entity_ids,
    graph_seeds,
    from_datetime,
    to_datetime,
    created_by,
    jurisdiction,
    created_at,
    updated_at
FROM {INVESTIGATIONS_TABLE}
ORDER BY updated_at DESC
"""

GET_SQL = f"""
SELECT
    id,
    name,
    description,
    selected_entity_ids,
    graph_seeds,
    from_datetime,
    to_datetime,
    created_by,
    jurisdiction,
    created_at,
    updated_at
FROM {INVESTIGATIONS_TABLE}
WHERE id = %(id)s
"""

COUNT_SQL = f"SELECT COUNT(*) AS total FROM {INVESTIGATIONS_TABLE}"

UPDATE_SQL = f"""
UPDATE {INVESTIGATIONS_TABLE}
SET
    name = %(name)s,
    description = %(description)s,
    selected_entity_ids = %(selected_entity_ids)s,
    graph_seeds = %(graph_seeds)s,
    from_datetime = %(from_datetime)s,
    to_datetime = %(to_datetime)s,
    updated_at = %(updated_at)s
WHERE id = %(id)s
RETURNING
    id,
    name,
    description,
    selected_entity_ids,
    graph_seeds,
    from_datetime,
    to_datetime,
    created_by,
    jurisdiction,
    created_at,
    updated_at
"""


class InvestigationRepository(Protocol):
    def ensure_schema(self) -> None: ...

    def count(self) -> int: ...

    def list_all(self) -> list[dict[str, Any]]: ...

    def get_by_id(self, investigation_id: str) -> dict[str, Any] | None: ...

    def insert(self, record: dict[str, Any]) -> dict[str, Any]: ...

    def update_by_id(
        self,
        investigation_id: str,
        patch: dict[str, Any],
    ) -> dict[str, Any] | None: ...


_repository: InvestigationRepository | None = None


def set_repository(repository: InvestigationRepository | None) -> None:
    global _repository
    _repository = repository


def get_repository() -> InvestigationRepository:
    global _repository
    if _repository is None:
        from app.core.config import postgres_configured, use_memory_store

        if postgres_configured() and not use_memory_store():
            _repository = PostgresInvestigationRepository()
        else:
            _repository = InMemoryInvestigationRepository()
    return _repository


def _format_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    return str(value)


def _normalize_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "description": row.get("description"),
        "selected_entity_ids": list(row.get("selected_entity_ids") or []),
        "graph_seeds": list(row.get("graph_seeds") or []),
        "from_datetime": row.get("from_datetime"),
        "to_datetime": row.get("to_datetime"),
        "created_by": str(row["created_by"]) if row.get("created_by") else None,
        "jurisdiction": row.get("jurisdiction"),
        "created_at": _format_timestamp(row["created_at"]),
        "updated_at": _format_timestamp(row["updated_at"]),
    }


def _parse_uuid(value: str) -> UUID:
    return UUID(str(value))


class PostgresInvestigationRepository:
    def ensure_schema(self) -> None:
        with get_cursor() as cursor:
            cursor.execute(SCHEMA_SQL)
            cursor.execute(INVESTIGATIONS_MIGRATION_SQL)
            cursor.execute(INVESTIGATIONS_JURISDICTION_MIGRATION_SQL)

    def count(self) -> int:
        with get_cursor() as cursor:
            cursor.execute(COUNT_SQL)
            row = cursor.fetchone()
            return int(row["total"])

    def list_all(self) -> list[dict[str, Any]]:
        with get_cursor() as cursor:
            cursor.execute(LIST_SQL)
            rows = cursor.fetchall()
            return [_normalize_record(row) for row in rows]

    def get_by_id(self, investigation_id: str) -> dict[str, Any] | None:
        with get_cursor() as cursor:
            cursor.execute(GET_SQL, {"id": _parse_uuid(investigation_id)})
            row = cursor.fetchone()
            return _normalize_record(row) if row else None

    def insert(self, record: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "id": _parse_uuid(record["id"]),
            "name": record["name"],
            "description": record.get("description"),
            "selected_entity_ids": record.get("selected_entity_ids") or [],
            "graph_seeds": record.get("graph_seeds") or [],
            "from_datetime": record.get("from_datetime"),
            "to_datetime": record.get("to_datetime"),
            "created_by": _parse_uuid(record["created_by"]) if record.get("created_by") else None,
            "jurisdiction": record.get("jurisdiction"),
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
        }
        with get_cursor() as cursor:
            cursor.execute(INSERT_SQL, payload)
        stored = self.get_by_id(str(record["id"]))
        if stored is None:
            raise RuntimeError("Failed to persist investigation record")
        return stored

    def update_by_id(
        self,
        investigation_id: str,
        patch: dict[str, Any],
    ) -> dict[str, Any] | None:
        current = self.get_by_id(investigation_id)
        if current is None:
            return None

        updated = {**current, **patch, "id": investigation_id}
        payload = {
            "id": _parse_uuid(investigation_id),
            "name": updated["name"],
            "description": updated.get("description"),
            "selected_entity_ids": updated.get("selected_entity_ids") or [],
            "graph_seeds": updated.get("graph_seeds") or [],
            "from_datetime": updated.get("from_datetime"),
            "to_datetime": updated.get("to_datetime"),
            "updated_at": updated["updated_at"],
        }
        with get_cursor() as cursor:
            cursor.execute(UPDATE_SQL, payload)
            row = cursor.fetchone()
            return _normalize_record(row) if row else None


class InMemoryInvestigationRepository:
    """Lightweight repository used by unit tests."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def ensure_schema(self) -> None:
        return None

    def count(self) -> int:
        return len(self._records)

    def list_all(self) -> list[dict[str, Any]]:
        records = list(self._records.values())
        records.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
        return [dict(record) for record in records]

    def get_by_id(self, investigation_id: str) -> dict[str, Any] | None:
        record = self._records.get(str(investigation_id))
        return dict(record) if record else None

    def insert(self, record: dict[str, Any]) -> dict[str, Any]:
        stored = dict(record)
        self._records[str(stored["id"])] = stored
        return dict(stored)

    def update_by_id(
        self,
        investigation_id: str,
        patch: dict[str, Any],
    ) -> dict[str, Any] | None:
        current = self.get_by_id(investigation_id)
        if current is None:
            return None
        current.update(patch)
        self._records[str(investigation_id)] = current
        return dict(current)


def import_legacy_json_records(
    repository: InvestigationRepository,
    json_path: Path | None = None,
) -> int:
    """Import legacy JSON investigations when PostgreSQL is empty."""
    if repository.count() > 0:
        return 0

    path = json_path or LEGACY_JSON_PATH
    if not path.exists():
        return 0

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return 0

    imported = 0
    for item in payload:
        if not isinstance(item, dict) or not item.get("id") or not item.get("name"):
            continue
        repository.insert(_normalize_record(item))
        imported += 1
    return imported


def initialize_investigations_store() -> None:
    from app.core.config import postgres_configured

    if not postgres_configured():
        return

    repository = get_repository()
    repository.ensure_schema()
    import_legacy_json_records(repository)
