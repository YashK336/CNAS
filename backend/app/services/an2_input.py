"""Normalize investigator AN-2 batches into the unstructured FIR ingest schema.

Accepts the existing JSON record array and CSV-style `fir_id,raw_text` input.
Does not run extraction or recurrence detection.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from app.services.unstructured_ingestion import UNSTRUCTURED_FIR_SOURCE

SOURCE_REF_KEYS = ("source_ref", "fir_id", "case_ref", "fir", "id")
TEXT_KEYS = ("text", "raw_text", "narrative", "narrative_text", "fir_text")
JURISDICTION_KEYS = ("jurisdiction", "juris", "state")
SOURCE_KEYS = ("source",)
DATE_KEYS = ("event_date", "date", "occurred_at", "valid_from")
KNOWN_INPUT_KEYS = frozenset(
    (*SOURCE_REF_KEYS, *TEXT_KEYS, *JURISDICTION_KEYS, *SOURCE_KEYS, *DATE_KEYS, "metadata")
)
DEFAULT_JURISDICTION = "UNSPECIFIED"


class An2InputError(ValueError):
    """Raised when an AN-2 batch cannot be normalized."""


def parse_an2_input(payload: Any) -> list[dict[str, Any]]:
    """Return canonical unstructured-FIR dicts ready for ingest_unstructured_fir."""
    items = _coerce_items(payload)
    return [_normalize_item(item, index) for index, item in enumerate(items, start=1)]


def _coerce_items(payload: Any) -> list[Any]:
    if payload is None:
        raise An2InputError("AN-2 payload is required")
    if isinstance(payload, str):
        return _items_from_text(payload)
    if isinstance(payload, dict):
        if isinstance(payload.get("records"), list):
            return payload["records"]
        if isinstance(payload.get("data"), list):
            return payload["data"]
        return [payload]
    if isinstance(payload, list):
        return payload
    raise An2InputError("AN-2 payload must be a JSON array, JSON object, or CSV text")


def _items_from_text(raw: str) -> list[Any]:
    text = raw.strip().lstrip("\ufeff")
    if not text:
        return []
    if text[0] in "[{":
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError as exc:
            raise An2InputError(f"invalid JSON AN-2 payload: {exc}") from exc
        return _coerce_items(loaded)
    return _items_from_csv(text)


def _items_from_csv(raw: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(raw))
    if reader.fieldnames is None:
        raise An2InputError("CSV AN-2 payload is missing a header row")
    rows: list[dict[str, str]] = []
    for row in reader:
        if row is None:
            continue
        normalized = {
            str(key).strip(): (value.strip() if isinstance(value, str) else value)
            for key, value in row.items()
            if key is not None and str(key).strip()
        }
        if not any(normalized.values()):
            continue
        rows.append(normalized)
    return rows


def _lookup(item: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    lowered = {str(key).strip().lower(): value for key, value in item.items()}
    for key in keys:
        value = lowered.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _normalize_item(item: Any, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise An2InputError(f"AN-2 record {index} must be an object")

    source = _lookup(item, SOURCE_KEYS) or UNSTRUCTURED_FIR_SOURCE
    source_ref = _lookup(item, SOURCE_REF_KEYS)
    text = _lookup(item, TEXT_KEYS)
    jurisdiction = _lookup(item, JURISDICTION_KEYS) or DEFAULT_JURISDICTION

    if not source_ref:
        raise An2InputError(f"AN-2 record {index} requires source_ref or fir_id")
    if not text:
        raise An2InputError(f"AN-2 record {index} requires text or raw_text")

    payload: dict[str, Any] = {
        "source": source,
        "source_ref": source_ref,
        "jurisdiction": jurisdiction,
        "text": text,
    }

    metadata = _collect_metadata(item)
    if metadata:
        payload["metadata"] = metadata
    return payload


def _collect_metadata(item: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    raw_metadata = item.get("metadata")
    if raw_metadata is None:
        raw_metadata = item.get("Metadata")
    if isinstance(raw_metadata, dict):
        metadata.update(raw_metadata)
    elif raw_metadata not in (None, ""):
        raise An2InputError("metadata must be a JSON object")

    for key in DATE_KEYS:
        if key in metadata and metadata[key] not in (None, ""):
            continue
        value = _lookup(item, (key,))
        if value:
            metadata[key] = value

    for key, value in item.items():
        lowered = str(key).strip().lower()
        if lowered in KNOWN_INPUT_KEYS or value in (None, ""):
            continue
        if lowered not in metadata:
            metadata[key] = value
    return metadata
