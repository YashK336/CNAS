"""PostgreSQL repository for entity resolution human-review items."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.core.database import get_cursor

REVIEWS_TABLE = "entity_resolution_reviews"
REJECTIONS_TABLE = "entity_resolution_rejections"

VALID_REVIEW_STATUSES = ("pending", "confirmed", "rejected")

REVIEWS_SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS {REVIEWS_TABLE} (
    id UUID PRIMARY KEY,
    candidate_value TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    reference_entity_id TEXT,
    proposed_entity_ids TEXT[] NOT NULL DEFAULT '{{}}',
    matching_method TEXT NOT NULL,
    match_score DOUBLE PRECISION,
    candidate_scores JSONB NOT NULL DEFAULT '{{}}',
    corroborating_evidence JSONB NOT NULL DEFAULT '{{}}',
    ambiguity_reason TEXT NOT NULL,
    jurisdiction TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'confirmed', 'rejected')),
    reviewer_id UUID,
    reviewed_at TIMESTAMPTZ,
    decision_reason TEXT,
    confirmed_entity_id TEXT,
    fingerprint TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
"""

REJECTIONS_SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS {REJECTIONS_TABLE} (
    fingerprint TEXT PRIMARY KEY,
    review_id UUID NOT NULL,
    rejected_at TIMESTAMPTZ NOT NULL,
    reviewer_id UUID
);
"""

INSERT_REVIEW_SQL = f"""
INSERT INTO {REVIEWS_TABLE} (
    id,
    candidate_value,
    entity_type,
    reference_entity_id,
    proposed_entity_ids,
    matching_method,
    match_score,
    candidate_scores,
    corroborating_evidence,
    ambiguity_reason,
    jurisdiction,
    status,
    reviewer_id,
    reviewed_at,
    decision_reason,
    confirmed_entity_id,
    fingerprint,
    created_at,
    updated_at
) VALUES (
    %(id)s,
    %(candidate_value)s,
    %(entity_type)s,
    %(reference_entity_id)s,
    %(proposed_entity_ids)s,
    %(matching_method)s,
    %(match_score)s,
    %(candidate_scores)s,
    %(corroborating_evidence)s,
    %(ambiguity_reason)s,
    %(jurisdiction)s,
    %(status)s,
    %(reviewer_id)s,
    %(reviewed_at)s,
    %(decision_reason)s,
    %(confirmed_entity_id)s,
    %(fingerprint)s,
    %(created_at)s,
    %(updated_at)s
)
"""

GET_REVIEW_SQL = f"""
SELECT
    id,
    candidate_value,
    entity_type,
    reference_entity_id,
    proposed_entity_ids,
    matching_method,
    match_score,
    candidate_scores,
    corroborating_evidence,
    ambiguity_reason,
    jurisdiction,
    status,
    reviewer_id,
    reviewed_at,
    decision_reason,
    confirmed_entity_id,
    fingerprint,
    created_at,
    updated_at
FROM {REVIEWS_TABLE}
WHERE id = %(id)s
"""

GET_BY_FINGERPRINT_SQL = f"""
SELECT
    id,
    candidate_value,
    entity_type,
    reference_entity_id,
    proposed_entity_ids,
    matching_method,
    match_score,
    candidate_scores,
    corroborating_evidence,
    ambiguity_reason,
    jurisdiction,
    status,
    reviewer_id,
    reviewed_at,
    decision_reason,
    confirmed_entity_id,
    fingerprint,
    created_at,
    updated_at
FROM {REVIEWS_TABLE}
WHERE fingerprint = %(fingerprint)s
ORDER BY created_at DESC
LIMIT 1
"""

LIST_PENDING_SQL = f"""
SELECT
    id,
    candidate_value,
    entity_type,
    reference_entity_id,
    proposed_entity_ids,
    matching_method,
    match_score,
    candidate_scores,
    corroborating_evidence,
    ambiguity_reason,
    jurisdiction,
    status,
    reviewer_id,
    reviewed_at,
    decision_reason,
    confirmed_entity_id,
    fingerprint,
    created_at,
    updated_at
FROM {REVIEWS_TABLE}
WHERE status = 'pending'
ORDER BY created_at ASC
"""

LIST_ALL_SQL = f"""
SELECT
    id,
    candidate_value,
    entity_type,
    reference_entity_id,
    proposed_entity_ids,
    matching_method,
    match_score,
    candidate_scores,
    corroborating_evidence,
    ambiguity_reason,
    jurisdiction,
    status,
    reviewer_id,
    reviewed_at,
    decision_reason,
    confirmed_entity_id,
    fingerprint,
    created_at,
    updated_at
FROM {REVIEWS_TABLE}
ORDER BY created_at ASC
"""

UPDATE_REVIEW_DECISION_SQL = f"""
UPDATE {REVIEWS_TABLE}
SET
    status = %(status)s,
    reviewer_id = %(reviewer_id)s,
    reviewed_at = %(reviewed_at)s,
    decision_reason = %(decision_reason)s,
    confirmed_entity_id = %(confirmed_entity_id)s,
    updated_at = %(updated_at)s
WHERE id = %(id)s
RETURNING
    id,
    candidate_value,
    entity_type,
    reference_entity_id,
    proposed_entity_ids,
    matching_method,
    match_score,
    candidate_scores,
    corroborating_evidence,
    ambiguity_reason,
    jurisdiction,
    status,
    reviewer_id,
    reviewed_at,
    decision_reason,
    confirmed_entity_id,
    fingerprint,
    created_at,
    updated_at
"""

INSERT_REJECTION_SQL = f"""
INSERT INTO {REJECTIONS_TABLE} (
    fingerprint,
    review_id,
    rejected_at,
    reviewer_id
) VALUES (
    %(fingerprint)s,
    %(review_id)s,
    %(rejected_at)s,
    %(reviewer_id)s
)
ON CONFLICT (fingerprint) DO NOTHING
"""

IS_REJECTED_SQL = f"""
SELECT 1
FROM {REJECTIONS_TABLE}
WHERE fingerprint = %(fingerprint)s
LIMIT 1
"""


class ReviewRepository(Protocol):
    def ensure_schema(self) -> None: ...

    def insert(self, record: dict[str, Any]) -> dict[str, Any]: ...

    def get_by_id(self, review_id: str) -> dict[str, Any] | None: ...

    def get_by_fingerprint(self, fingerprint: str) -> dict[str, Any] | None: ...

    def list_pending(self) -> list[dict[str, Any]]: ...

    def list_all(self) -> list[dict[str, Any]]: ...

    def update_decision(self, review_id: str, updates: dict[str, Any]) -> dict[str, Any]: ...

    def is_rejected(self, fingerprint: str) -> bool: ...

    def register_rejection(
        self,
        *,
        fingerprint: str,
        review_id: str,
        reviewer_id: str | None,
        rejected_at: str,
    ) -> None: ...


_repository: ReviewRepository | None = None


def set_repository(repository: ReviewRepository | None) -> None:
    global _repository
    _repository = repository


def get_review_repository() -> ReviewRepository:
    global _repository
    if _repository is None:
        from app.core.config import postgres_configured, use_memory_store

        if postgres_configured() and not use_memory_store():
            _repository = PostgresReviewRepository()
        else:
            _repository = InMemoryReviewRepository()
    return _repository


def _format_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    return str(value)


def _parse_uuid(value: str) -> UUID:
    return UUID(str(value))


def _load_json(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, str):
        loaded = json.loads(value)
        return loaded if isinstance(loaded, dict) else {}
    if isinstance(value, dict):
        return value
    return {}


def _normalize_status(status: str) -> str:
    normalized = str(status).strip().lower()
    if normalized not in VALID_REVIEW_STATUSES:
        raise ValueError(f"status must be one of {', '.join(VALID_REVIEW_STATUSES)}")
    return normalized


def _normalize_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "candidate_value": row["candidate_value"],
        "entity_type": row["entity_type"],
        "reference_entity_id": row.get("reference_entity_id"),
        "proposed_entity_ids": list(row.get("proposed_entity_ids") or []),
        "matching_method": row["matching_method"],
        "match_score": float(row["match_score"]) if row.get("match_score") is not None else None,
        "candidate_scores": {
            str(key): float(value)
            for key, value in _load_json(row.get("candidate_scores")).items()
        },
        "corroborating_evidence": _load_json(row.get("corroborating_evidence")),
        "ambiguity_reason": row["ambiguity_reason"],
        "jurisdiction": row.get("jurisdiction"),
        "status": row["status"],
        "reviewer_id": str(row["reviewer_id"]) if row.get("reviewer_id") else None,
        "reviewed_at": _format_timestamp(row["reviewed_at"]) if row.get("reviewed_at") else None,
        "decision_reason": row.get("decision_reason"),
        "confirmed_entity_id": row.get("confirmed_entity_id"),
        "fingerprint": row["fingerprint"],
        "created_at": _format_timestamp(row["created_at"]),
        "updated_at": _format_timestamp(row["updated_at"]),
    }


class PostgresReviewRepository:
    def ensure_schema(self) -> None:
        with get_cursor() as cursor:
            cursor.execute(REVIEWS_SCHEMA_SQL)
            cursor.execute(REJECTIONS_SCHEMA_SQL)

    def insert(self, record: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "id": _parse_uuid(record["id"]),
            "candidate_value": record["candidate_value"],
            "entity_type": record["entity_type"],
            "reference_entity_id": record.get("reference_entity_id"),
            "proposed_entity_ids": list(record.get("proposed_entity_ids") or []),
            "matching_method": record["matching_method"],
            "match_score": record.get("match_score"),
            "candidate_scores": json.dumps(record.get("candidate_scores") or {}),
            "corroborating_evidence": json.dumps(record.get("corroborating_evidence") or {}),
            "ambiguity_reason": record["ambiguity_reason"],
            "jurisdiction": record.get("jurisdiction"),
            "status": _normalize_status(record["status"]),
            "reviewer_id": _parse_uuid(record["reviewer_id"]) if record.get("reviewer_id") else None,
            "reviewed_at": record.get("reviewed_at"),
            "decision_reason": record.get("decision_reason"),
            "confirmed_entity_id": record.get("confirmed_entity_id"),
            "fingerprint": record["fingerprint"],
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
        }
        with get_cursor() as cursor:
            cursor.execute(INSERT_REVIEW_SQL, payload)
        stored = self.get_by_id(str(record["id"]))
        if stored is None:
            raise RuntimeError("Failed to persist review record")
        return stored

    def get_by_id(self, review_id: str) -> dict[str, Any] | None:
        with get_cursor() as cursor:
            cursor.execute(GET_REVIEW_SQL, {"id": _parse_uuid(review_id)})
            row = cursor.fetchone()
            return _normalize_record(row) if row else None

    def get_by_fingerprint(self, fingerprint: str) -> dict[str, Any] | None:
        with get_cursor() as cursor:
            cursor.execute(GET_BY_FINGERPRINT_SQL, {"fingerprint": fingerprint})
            row = cursor.fetchone()
            return _normalize_record(row) if row else None

    def list_pending(self) -> list[dict[str, Any]]:
        with get_cursor() as cursor:
            cursor.execute(LIST_PENDING_SQL)
            rows = cursor.fetchall()
            return [_normalize_record(row) for row in rows]

    def list_all(self) -> list[dict[str, Any]]:
        with get_cursor() as cursor:
            cursor.execute(LIST_ALL_SQL)
            rows = cursor.fetchall()
            return [_normalize_record(row) for row in rows]

    def update_decision(self, review_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "id": _parse_uuid(review_id),
            "status": _normalize_status(updates["status"]),
            "reviewer_id": _parse_uuid(updates["reviewer_id"]) if updates.get("reviewer_id") else None,
            "reviewed_at": updates["reviewed_at"],
            "decision_reason": updates.get("decision_reason"),
            "confirmed_entity_id": updates.get("confirmed_entity_id"),
            "updated_at": updates["updated_at"],
        }
        with get_cursor() as cursor:
            cursor.execute(UPDATE_REVIEW_DECISION_SQL, payload)
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("Review record not found for update")
            return _normalize_record(row)

    def is_rejected(self, fingerprint: str) -> bool:
        with get_cursor() as cursor:
            cursor.execute(IS_REJECTED_SQL, {"fingerprint": fingerprint})
            return cursor.fetchone() is not None

    def register_rejection(
        self,
        *,
        fingerprint: str,
        review_id: str,
        reviewer_id: str | None,
        rejected_at: str,
    ) -> None:
        payload = {
            "fingerprint": fingerprint,
            "review_id": _parse_uuid(review_id),
            "rejected_at": rejected_at,
            "reviewer_id": _parse_uuid(reviewer_id) if reviewer_id else None,
        }
        with get_cursor() as cursor:
            cursor.execute(INSERT_REJECTION_SQL, payload)


class InMemoryReviewRepository:
    """Lightweight repository used by unit tests."""

    def __init__(self) -> None:
        self._records_by_id: dict[str, dict[str, Any]] = {}
        self._records_by_fingerprint: dict[str, dict[str, Any]] = {}
        self._rejections: set[str] = set()
        self._fail_on_insert = False
        self._fail_on_update = False

    def ensure_schema(self) -> None:
        return None

    def insert(self, record: dict[str, Any]) -> dict[str, Any]:
        if self._fail_on_insert:
            raise RuntimeError("review store unavailable")
        stored = dict(record)
        self._records_by_id[str(stored["id"])] = stored
        self._records_by_fingerprint[stored["fingerprint"]] = stored
        return dict(stored)

    def get_by_id(self, review_id: str) -> dict[str, Any] | None:
        record = self._records_by_id.get(str(review_id))
        return dict(record) if record else None

    def get_by_fingerprint(self, fingerprint: str) -> dict[str, Any] | None:
        record = self._records_by_fingerprint.get(fingerprint)
        return dict(record) if record else None

    def list_pending(self) -> list[dict[str, Any]]:
        pending = [
            dict(record)
            for record in self._records_by_id.values()
            if record.get("status") == "pending"
        ]
        pending.sort(key=lambda item: item.get("created_at") or "")
        return pending

    def list_all(self) -> list[dict[str, Any]]:
        records = [dict(record) for record in self._records_by_id.values()]
        records.sort(key=lambda item: item.get("created_at") or "")
        return records

    def update_decision(self, review_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        if self._fail_on_update:
            raise RuntimeError("review store unavailable")
        record = self._records_by_id.get(str(review_id))
        if record is None:
            raise RuntimeError("Review record not found for update")
        record.update(updates)
        self._records_by_fingerprint[record["fingerprint"]] = record
        return dict(record)

    def is_rejected(self, fingerprint: str) -> bool:
        return fingerprint in self._rejections

    def register_rejection(
        self,
        *,
        fingerprint: str,
        review_id: str,
        reviewer_id: str | None,
        rejected_at: str,
    ) -> None:
        self._rejections.add(fingerprint)


def initialize_review_store() -> None:
    from app.core.config import postgres_configured

    if not postgres_configured():
        return

    repository = get_review_repository()
    repository.ensure_schema()
