"""
Deterministic normalization and content hashing for raw CSV records.

Each normalized record carries provenance metadata while preserving the
original row payload in `data`. Duplicate hashes are detectable; records are
not discarded at this layer.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, TypedDict

import pandas as pd

# Natural keys used to build stable record_id values per dataset.
RECORD_ID_FIELDS: dict[str, list[str]] = {
    "persons": ["person_id"],
    "vehicles": ["vehicle_no"],
    "cdr": ["caller_id", "receiver_id", "timestamp"],
    "finance": ["sender_id", "receiver_id", "date", "amount"],
    "fir": ["fir_id"],
    "social": ["user_id", "connected_user_id", "date", "interaction_type"],
    "surveillance": ["event_id"],
    "entity_mapping": ["entity_id", "entity_type", "source", "source_id"],
}


class NormalizedRecord(TypedDict):
    source: str
    record_id: str
    ingested_at: str
    content_hash: str
    data: dict[str, Any]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_cell(value: Any) -> Any:
    """Mirror ingestion.load_csv: pandas NaN becomes JSON-safe null."""
    if value is None:
        return None

    if isinstance(value, float) and pd.isna(value):
        return None

    if isinstance(value, str):
        text = value.strip()
        return text if text != "" else None

    # Pandas timestamps and numpy scalars become stable strings.
    if hasattr(value, "item"):
        return clean_cell(value.item())

    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()

    return value


def row_to_data(row: pd.Series) -> dict[str, Any]:
    return {str(column): clean_cell(row[column]) for column in row.index}


def build_record_id(source: str, data: dict[str, Any], row_index: int) -> str:
    fields = RECORD_ID_FIELDS.get(source, [])

    if fields:
        parts = []
        for field in fields:
            value = data.get(field)
            if value is None:
                break
            parts.append(str(value))
        else:
            return f"{source}:" + ":".join(parts)

    return f"{source}:row:{row_index}"


def hash_record_content(source: str, data: dict[str, Any]) -> str:
    """Deterministic SHA-256 over canonical JSON.

    Only `source` and sorted `data` fields participate — not ingested_at or
    record_id — so the same source row always yields the same hash.
    """
    payload = {
        "source": source,
        "data": {key: data[key] for key in sorted(data)},
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalize_row(
    source: str,
    row: pd.Series,
    row_index: int,
    ingested_at: str | None = None,
) -> NormalizedRecord:
    data = row_to_data(row)
    record_id = build_record_id(source, data, row_index)

    return NormalizedRecord(
        source=source,
        record_id=record_id,
        ingested_at=ingested_at or utc_now_iso(),
        content_hash=hash_record_content(source, data),
        data=data,
    )


def normalize_dataframe(
    source: str,
    df: pd.DataFrame,
    ingested_at: str | None = None,
) -> list[NormalizedRecord]:
    timestamp = ingested_at or utc_now_iso()

    return [
        normalize_row(source, row, index, ingested_at=timestamp)
        for index, row in df.iterrows()
    ]


def find_duplicate_hashes(
    records: list[NormalizedRecord],
) -> dict[str, list[str]]:
    """
    Map content_hash -> record_ids for hashes seen more than once.

    All matching records are retained; this only reports duplicates.
    """
    by_hash: dict[str, list[str]] = {}

    for record in records:
        by_hash.setdefault(record["content_hash"], []).append(record["record_id"])

    return {
        content_hash: record_ids
        for content_hash, record_ids in by_hash.items()
        if len(record_ids) > 1
    }
