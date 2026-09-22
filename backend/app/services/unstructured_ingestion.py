"""
Unstructured FIR / intelligence text ingestion contract.

Accepts raw narrative text with provenance and returns a NormalizedRecord
envelope compatible with the existing extraction pipeline. Original text is
stored verbatim; only validation trims/checks required scalar fields.
"""

from __future__ import annotations

from typing import Any, TypedDict

from app.services.normalization import (
    NormalizedRecord,
    hash_record_content,
    utc_now_iso,
)

UNSTRUCTURED_FIR_SOURCE = "unstructured_fir"


class UnstructuredFirInput(TypedDict, total=False):
    """Typed contract for unstructured FIR/intelligence ingestion."""

    source: str
    source_ref: str
    jurisdiction: str
    text: str
    metadata: dict[str, Any]


class UnstructuredIngestionValidationError(ValueError):
    """Raised when an unstructured FIR payload fails contract validation."""


REQUIRED_FIELDS = ("source", "source_ref", "jurisdiction", "text")


def _require_non_empty_string(
    payload: dict[str, Any],
    field: str,
) -> str:
    if field not in payload:
        raise UnstructuredIngestionValidationError(f"{field} is required")

    value = payload[field]
    if not isinstance(value, str):
        raise UnstructuredIngestionValidationError(f"{field} must be a string")

    if value.strip() == "":
        raise UnstructuredIngestionValidationError(f"{field} must not be empty")

    return value


def _validate_metadata(payload: dict[str, Any]) -> dict[str, Any] | None:
    if "metadata" not in payload or payload["metadata"] is None:
        return None

    metadata = payload["metadata"]
    if not isinstance(metadata, dict):
        raise UnstructuredIngestionValidationError("metadata must be a JSON object")

    return dict(metadata)


def build_unstructured_record_id(source: str, source_ref: str) -> str:
    return f"{source}:{source_ref}"


def build_unstructured_data(
    *,
    text: str,
    source_ref: str,
    jurisdiction: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "text": text,
        "source_ref": source_ref,
        "jurisdiction": jurisdiction,
    }
    if metadata:
        data["metadata"] = metadata
    return data


def ingest_unstructured_fir(
    payload: UnstructuredFirInput | dict[str, Any],
    *,
    ingested_at: str | None = None,
) -> NormalizedRecord:
    """Validate and normalize one unstructured FIR/intelligence document."""
    if not isinstance(payload, dict):
        raise UnstructuredIngestionValidationError("payload must be an object")

    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise UnstructuredIngestionValidationError(
            f"missing required fields: {', '.join(missing)}"
        )

    source = _require_non_empty_string(payload, "source")
    source_ref = _require_non_empty_string(payload, "source_ref")
    jurisdiction = _require_non_empty_string(payload, "jurisdiction")
    text = _require_non_empty_string(payload, "text")
    metadata = _validate_metadata(payload)

    data = build_unstructured_data(
        text=text,
        source_ref=source_ref,
        jurisdiction=jurisdiction,
        metadata=metadata,
    )

    return NormalizedRecord(
        source=source,
        record_id=build_unstructured_record_id(source, source_ref),
        ingested_at=ingested_at or utc_now_iso(),
        content_hash=hash_record_content(source, data),
        data=data,
    )
