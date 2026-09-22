"""PostgreSQL repository for CNAS users."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.core.database import get_cursor

USERS_TABLE = "users"
VALID_ROLES = ("ADMIN", "ANALYST", "VIEWER")

USERS_SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS {USERS_TABLE} (
    id UUID PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('ADMIN', 'ANALYST', 'VIEWER')),
    jurisdictions TEXT[] NOT NULL DEFAULT '{{}}',
    created_at TIMESTAMPTZ NOT NULL
);
"""

USERS_MIGRATION_SQL = (
    f"ALTER TABLE {USERS_TABLE} "
    "ADD COLUMN IF NOT EXISTS jurisdictions TEXT[] NOT NULL DEFAULT '{}';"
)

INSERT_USER_SQL = f"""
INSERT INTO {USERS_TABLE} (
    id,
    username,
    password_hash,
    role,
    jurisdictions,
    created_at
) VALUES (
    %(id)s,
    %(username)s,
    %(password_hash)s,
    %(role)s,
    %(jurisdictions)s,
    %(created_at)s
)
"""

GET_USER_BY_ID_SQL = f"""
SELECT id, username, password_hash, role, jurisdictions, created_at
FROM {USERS_TABLE}
WHERE id = %(id)s
"""

GET_USER_BY_USERNAME_SQL = f"""
SELECT id, username, password_hash, role, jurisdictions, created_at
FROM {USERS_TABLE}
WHERE username = %(username)s
"""

COUNT_USERS_SQL = f"SELECT COUNT(*) AS total FROM {USERS_TABLE}"

LIST_USERS_SQL = f"""
SELECT id, username, password_hash, role, jurisdictions, created_at
FROM {USERS_TABLE}
ORDER BY username
"""


class UserRepository(Protocol):
    def ensure_schema(self) -> None: ...

    def count(self) -> int: ...

    def get_by_id(self, user_id: str) -> dict[str, Any] | None: ...

    def get_by_username(self, username: str) -> dict[str, Any] | None: ...

    def list_all(self) -> list[dict[str, Any]]: ...

    def insert(self, record: dict[str, Any]) -> dict[str, Any]: ...


_repository: UserRepository | None = None


def set_repository(repository: UserRepository | None) -> None:
    global _repository
    _repository = repository


def get_user_repository() -> UserRepository:
    global _repository
    if _repository is None:
        _repository = PostgresUserRepository()
    return _repository


def _format_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    return str(value)


def _normalize_role(role: str) -> str:
    normalized = str(role).strip().upper()
    if normalized not in VALID_ROLES:
        raise ValueError(f"role must be one of {', '.join(VALID_ROLES)}")
    return normalized


def _normalize_jurisdictions(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("jurisdictions must be an array")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError("jurisdictions must contain strings")
        trimmed = item.strip()
        if trimmed:
            normalized.append(trimmed)
    return normalized


def _normalize_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "username": row["username"],
        "password_hash": row["password_hash"],
        "role": row["role"],
        "jurisdictions": list(row.get("jurisdictions") or []),
        "created_at": _format_timestamp(row["created_at"]),
    }


def _parse_uuid(value: str) -> UUID:
    return UUID(str(value))


class PostgresUserRepository:
    def ensure_schema(self) -> None:
        with get_cursor() as cursor:
            cursor.execute(USERS_SCHEMA_SQL)
            cursor.execute(USERS_MIGRATION_SQL)

    def count(self) -> int:
        with get_cursor() as cursor:
            cursor.execute(COUNT_USERS_SQL)
            row = cursor.fetchone()
            return int(row["total"])

    def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        with get_cursor() as cursor:
            cursor.execute(GET_USER_BY_ID_SQL, {"id": _parse_uuid(user_id)})
            row = cursor.fetchone()
            return _normalize_record(row) if row else None

    def get_by_username(self, username: str) -> dict[str, Any] | None:
        with get_cursor() as cursor:
            cursor.execute(GET_USER_BY_USERNAME_SQL, {"username": username})
            row = cursor.fetchone()
            return _normalize_record(row) if row else None

    def list_all(self) -> list[dict[str, Any]]:
        with get_cursor() as cursor:
            cursor.execute(LIST_USERS_SQL)
            return [_normalize_record(row) for row in cursor.fetchall()]

    def insert(self, record: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "id": _parse_uuid(record["id"]),
            "username": record["username"],
            "password_hash": record["password_hash"],
            "role": _normalize_role(record["role"]),
            "jurisdictions": _normalize_jurisdictions(record.get("jurisdictions")),
            "created_at": record["created_at"],
        }
        with get_cursor() as cursor:
            cursor.execute(INSERT_USER_SQL, payload)
        stored = self.get_by_id(str(record["id"]))
        if stored is None:
            raise RuntimeError("Failed to persist user record")
        return stored


class InMemoryUserRepository:
    """Lightweight repository used by unit tests."""

    def __init__(self) -> None:
        self._records_by_id: dict[str, dict[str, Any]] = {}
        self._records_by_username: dict[str, dict[str, Any]] = {}

    def ensure_schema(self) -> None:
        return None

    def count(self) -> int:
        return len(self._records_by_id)

    def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        record = self._records_by_id.get(str(user_id))
        return dict(record) if record else None

    def get_by_username(self, username: str) -> dict[str, Any] | None:
        record = self._records_by_username.get(username)
        return dict(record) if record else None

    def list_all(self) -> list[dict[str, Any]]:
        return [
            dict(record)
            for record in sorted(
                self._records_by_id.values(),
                key=lambda item: str(item.get("username") or ""),
            )
        ]

    def insert(self, record: dict[str, Any]) -> dict[str, Any]:
        stored = dict(record)
        if "jurisdictions" not in stored:
            stored["jurisdictions"] = []
        self._records_by_id[str(stored["id"])] = stored
        self._records_by_username[stored["username"]] = stored
        return dict(stored)


def seed_default_users() -> None:
    """Bootstrap local dev users when the users table is empty."""
    from datetime import datetime, timezone
    from uuid import uuid4

    from app.services.auth import hash_password

    repository = get_user_repository()
    if repository.count() > 0:
        return

    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    defaults = (
        {
            "username": "admin",
            "password": "admin-pass",
            "role": "ADMIN",
            "jurisdictions": [],
        },
        {
            "username": "analyst",
            "password": "analyst-pass",
            "role": "ANALYST",
            "jurisdictions": ["DEL"],
        },
        {
            "username": "viewer",
            "password": "viewer-pass",
            "role": "VIEWER",
            "jurisdictions": ["MUM"],
        },
    )
    for entry in defaults:
        repository.insert(
            {
                "id": str(uuid4()),
                "username": entry["username"],
                "password_hash": hash_password(entry["password"]),
                "role": entry["role"],
                "jurisdictions": entry["jurisdictions"],
                "created_at": created_at,
            }
        )


def initialize_users_store() -> None:
    from app.core.config import postgres_configured

    if not postgres_configured():
        return

    repository = get_user_repository()
    repository.ensure_schema()
    seed_default_users()
