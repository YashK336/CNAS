"""Import batch store (draft → result). Raw file bytes are not retained.

Production uses PostgreSQL via the existing raw-psycopg repositories.
In-memory storage remains available for tests and CNAS_USE_MEMORY_STORE.
"""

from __future__ import annotations

import json
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.core.database import get_cursor
from app.services.normalization import utc_now_iso

STATUS_DRAFT = "draft"
STATUS_VALIDATING = "validating"
STATUS_READY = "ready"
STATUS_IMPORTING = "importing"
STATUS_COMPLETE = "complete"
STATUS_COMPLETE_WARNINGS = "completed_with_warnings"
STATUS_PARTIAL = "partially_imported"
STATUS_FAILED = "failed"

VISIBLE_STATUSES = (
    STATUS_DRAFT,
    STATUS_VALIDATING,
    STATUS_READY,
    STATUS_IMPORTING,
    STATUS_COMPLETE,
    STATUS_COMPLETE_WARNINGS,
    STATUS_PARTIAL,
    STATUS_FAILED,
)

IMPORT_BATCHES_TABLE = "import_batches"

IMPORT_SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS {IMPORT_BATCHES_TABLE} (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL,
    uploader_id TEXT,
    record JSONB NOT NULL
);
"""

INSERT_SQL = f"""
INSERT INTO {IMPORT_BATCHES_TABLE} (
    id, created_at, updated_at, status, uploader_id, record
) VALUES (
    %(id)s, %(created_at)s, %(updated_at)s, %(status)s, %(uploader_id)s, %(record)s::jsonb
)
"""

GET_SQL = f"""
SELECT id, created_at, updated_at, status, uploader_id, record
FROM {IMPORT_BATCHES_TABLE}
WHERE id = %(id)s
"""

LIST_SQL = f"""
SELECT id, created_at, updated_at, status, uploader_id, record
FROM {IMPORT_BATCHES_TABLE}
ORDER BY created_at DESC
"""

UPDATE_SQL = f"""
UPDATE {IMPORT_BATCHES_TABLE}
SET
    updated_at = %(updated_at)s,
    status = %(status)s,
    uploader_id = %(uploader_id)s,
    record = %(record)s::jsonb
WHERE id = %(id)s
"""


class ImportNotFoundError(LookupError):
    pass


class ImportAccessDenied(PermissionError):
    pass


class ImportRepository(Protocol):
    def ensure_schema(self) -> None: ...

    def insert(self, record: dict[str, Any]) -> dict[str, Any]: ...

    def get(self, import_id: str) -> dict[str, Any]: ...

    def update(self, import_id: str, patch: dict[str, Any]) -> dict[str, Any]: ...

    def list_all(self) -> list[dict[str, Any]]: ...


_repository: ImportRepository | None = None


def set_import_repository(repository: ImportRepository | None) -> None:
    global _repository
    _repository = repository


def get_import_repository() -> ImportRepository:
    global _repository
    if _repository is None:
        from app.core.config import postgres_configured, use_memory_store

        if postgres_configured() and not use_memory_store():
            _repository = PostgresImportRepository()
        else:
            _repository = InMemoryImportRepository()
    return _repository


def _parse_record(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, str):
        loaded = json.loads(value)
        return dict(loaded) if isinstance(loaded, dict) else {}
    if isinstance(value, dict):
        return dict(value)
    return {}


def _row_to_record(row: dict[str, Any]) -> dict[str, Any]:
    record = _parse_record(row.get("record"))
    record["id"] = str(row["id"])
    if row.get("created_at") is not None:
        record["created_at"] = record.get("created_at") or str(row["created_at"])
    if row.get("updated_at") is not None:
        record["updated_at"] = record.get("updated_at") or str(row["updated_at"])
    return record


def _write_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": UUID(str(record["id"])),
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "status": record.get("status") or STATUS_DRAFT,
        "uploader_id": record.get("uploader_id"),
        "record": json.dumps(record, ensure_ascii=False, default=str),
    }


class PostgresImportRepository:
    def ensure_schema(self) -> None:
        with get_cursor() as cursor:
            cursor.execute(IMPORT_SCHEMA_SQL)

    def insert(self, record: dict[str, Any]) -> dict[str, Any]:
        stored = dict(record)
        with get_cursor() as cursor:
            cursor.execute(INSERT_SQL, _write_payload(stored))
        return dict(stored)

    def get(self, import_id: str) -> dict[str, Any]:
        with get_cursor() as cursor:
            cursor.execute(GET_SQL, {"id": UUID(str(import_id))})
            row = cursor.fetchone()
        if row is None:
            raise ImportNotFoundError("Import batch not found")
        return _row_to_record(row)

    def update(self, import_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        current = self.get(import_id)
        current.update(patch)
        current["updated_at"] = utc_now_iso()
        with get_cursor() as cursor:
            cursor.execute(UPDATE_SQL, _write_payload(current))
        return dict(current)

    def list_all(self) -> list[dict[str, Any]]:
        with get_cursor() as cursor:
            cursor.execute(LIST_SQL)
            rows = cursor.fetchall()
        return [_row_to_record(row) for row in rows]


class InMemoryImportRepository:
    """Process-local store used by unit tests."""

    def __init__(self) -> None:
        self._batches: dict[str, dict[str, Any]] = {}

    def ensure_schema(self) -> None:
        return None

    def insert(self, record: dict[str, Any]) -> dict[str, Any]:
        stored = dict(record)
        self._batches[str(stored["id"])] = stored
        return dict(stored)

    def get(self, import_id: str) -> dict[str, Any]:
        stored = self._batches.get(str(import_id))
        if stored is None:
            raise ImportNotFoundError("Import batch not found")
        return stored

    def update(self, import_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        stored = self.get(import_id)
        stored.update(patch)
        stored["updated_at"] = utc_now_iso()
        return stored

    def list_all(self) -> list[dict[str, Any]]:
        return sorted(
            self._batches.values(),
            key=lambda item: str(item.get("created_at") or ""),
            reverse=True,
        )


def reset_import_store() -> None:
    """Replace the active store with an empty in-memory store. Used by tests."""
    set_import_repository(InMemoryImportRepository())


def create_batch(record: dict[str, Any]) -> dict[str, Any]:
    batch_id = str(uuid4())
    stored = {
        "id": batch_id,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        **record,
    }
    return get_import_repository().insert(stored)


def get_batch(import_id: str) -> dict[str, Any]:
    return get_import_repository().get(import_id)


def save_batch(import_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    return get_import_repository().update(import_id, patch)


def list_batches() -> list[dict[str, Any]]:
    return get_import_repository().list_all()


def initialize_import_store() -> None:
    from app.core.config import postgres_configured, use_memory_store

    if not postgres_configured() or use_memory_store():
        if _repository is None:
            set_import_repository(InMemoryImportRepository())
        return

    repository = PostgresImportRepository()
    set_import_repository(repository)
    repository.ensure_schema()
