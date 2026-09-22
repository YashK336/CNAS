"""
Layer 2 entity extraction from normalized ingestion records.

Deterministic regex extraction runs first for Indian identifiers. spaCy
transformer NER adds Person, Location, Organisation and Event candidates
with character offsets and confidence scores.
"""

from __future__ import annotations

import re
from typing import Any, TypedDict

from app.services.extraction_config import (
    CONFIDENCE_REGEX,
    EXTRACTION_METHOD_REGEX,
    NER_ENTITY_TYPES,
)
from app.services.ner_extraction import extract_ner_spans, ner_span_to_candidate_fields
from app.services.resolution_config import IDENTIFIER_ENTITY_TYPES
from app.services.normalization import NormalizedRecord

ENTITY_TYPES = (
    "phone",
    "vehicle",
    "bank_account",
    "ifsc",
    *sorted(NER_ENTITY_TYPES),
)

# Indian mobile: +91-XXXXX-XXXXX, +91 XXXXXXXXXX, or standalone 10-digit mobile.
PHONE_PATTERN = re.compile(
    r"(?:\+91[-\s]?\d{5}[-\s]?\d{5}|\+91[-\s]?\d{10}|\b[6-9]\d{9}\b)",
    re.IGNORECASE,
)

# Indian vehicle registration (classic series): DL11AB1001, KA12AB1002, etc.
VEHICLE_PATTERN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z]{1,3}\d{4}\b", re.IGNORECASE)

# Dataset bank token and generic account numbers in account-named fields.
BANK_ACC_PATTERN = re.compile(r"\bACC\d{6,}\b", re.IGNORECASE)
BANK_NUMERIC_PATTERN = re.compile(r"\b\d{9,18}\b")

# Indian Financial System Code: 4 letters + 0 + 6 alphanumeric.
IFSC_PATTERN = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b", re.IGNORECASE)


class EntityCandidate(TypedDict, total=False):
    entity_type: str
    value: str
    normalized_value: str
    confidence: float
    source: str
    record_id: str
    start: int
    end: int
    offset: int
    source_text: str
    extraction_method: str
    resolution_eligible: bool


PROVENANCE_DATA_FIELDS = frozenset({"source_ref", "jurisdiction", "metadata"})
UNSTRUCTURED_TEXT_FIELD = "text"

ACCOUNT_CONTEXT_PATTERN = re.compile(
    r"\b(?:account|a/c|acct|bank\s+account)\b",
    re.IGNORECASE,
)
PHONE_FALSE_POSITIVE_PREFIX = re.compile(
    r"\b(?:case|fir|crime|dated|date|no\.?|number|ref)\b",
    re.IGNORECASE,
)


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 12 and digits.startswith("91"):
        digits = digits[-10:]
    if len(digits) == 10:
        return f"+91{digits}"
    return re.sub(r"\s+", "", value.strip())


def normalize_vehicle(value: str) -> str:
    return re.sub(r"\s+", "", value.strip()).upper()


def normalize_bank_account(value: str) -> str:
    return re.sub(r"\s+", "", value.strip()).upper()


def normalize_ifsc(value: str) -> str:
    return re.sub(r"\s+", "", value.strip()).upper()


def candidate_normalized_value(candidate: EntityCandidate) -> str:
    """Return the normalized identifier used by resolution and matching."""
    normalized = candidate.get("normalized_value")
    if normalized:
        return normalized
    return candidate["value"]


def _is_account_field(field: str) -> bool:
    return "account" in field.lower()


def _spans_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    return start_a < end_b and start_b < end_a


def _has_account_context(text: str, start: int) -> bool:
    window = text[max(0, start - 48):start]
    return bool(ACCOUNT_CONTEXT_PATTERN.search(window))


def _should_reject_phone_in_prose(text: str, start: int, end: int) -> bool:
    prefix = text[max(0, start - 32):start]
    if PHONE_FALSE_POSITIVE_PREFIX.search(prefix):
        return True
    if start > 0 and text[start - 1].isdigit():
        return True
    if end < len(text) and text[end].isdigit():
        return True
    return False


def _should_extract_numeric_account(
    text: str,
    start: int,
    *,
    field: str | None,
    prose_mode: bool,
) -> bool:
    if field and _is_account_field(field):
        return True
    return prose_mode and _has_account_context(text, start)


def _append_match(
    candidates: list[EntityCandidate],
    *,
    entity_type: str,
    raw: str,
    normalize,
    source: str,
    record_id: str,
    start: int,
) -> None:
    normalized = normalize(raw)
    end = start + len(raw)
    candidates.append(
        EntityCandidate(
            entity_type=entity_type,
            value=raw,
            normalized_value=normalized,
            confidence=CONFIDENCE_REGEX,
            source=source,
            record_id=record_id,
            start=start,
            end=end,
            offset=start,
            source_text=raw,
            extraction_method=EXTRACTION_METHOD_REGEX,
            resolution_eligible=True,
        )
    )


def _extract_regex_from_text(
    text: str,
    *,
    source: str,
    record_id: str,
    field: str | None = None,
    prose_mode: bool = False,
) -> list[EntityCandidate]:
    if not text:
        return []

    candidates: list[EntityCandidate] = []

    for match in PHONE_PATTERN.finditer(text):
        raw = match.group(0)
        if prose_mode and _should_reject_phone_in_prose(text, match.start(), match.end()):
            continue
        _append_match(
            candidates,
            entity_type="phone",
            raw=raw,
            normalize=normalize_phone,
            source=source,
            record_id=record_id,
            start=match.start(),
        )

    for match in VEHICLE_PATTERN.finditer(text):
        _append_match(
            candidates,
            entity_type="vehicle",
            raw=match.group(0),
            normalize=normalize_vehicle,
            source=source,
            record_id=record_id,
            start=match.start(),
        )

    for match in BANK_ACC_PATTERN.finditer(text):
        _append_match(
            candidates,
            entity_type="bank_account",
            raw=match.group(0),
            normalize=normalize_bank_account,
            source=source,
            record_id=record_id,
            start=match.start(),
        )

    for match in BANK_NUMERIC_PATTERN.finditer(text):
        raw = match.group(0)
        if BANK_ACC_PATTERN.fullmatch(raw):
            continue
        if not _should_extract_numeric_account(
            text,
            match.start(),
            field=field,
            prose_mode=prose_mode,
        ):
            continue
        _append_match(
            candidates,
            entity_type="bank_account",
            raw=raw,
            normalize=normalize_bank_account,
            source=source,
            record_id=record_id,
            start=match.start(),
        )

    for match in IFSC_PATTERN.finditer(text):
        _append_match(
            candidates,
            entity_type="ifsc",
            raw=match.group(0),
            normalize=normalize_ifsc,
            source=source,
            record_id=record_id,
            start=match.start(),
        )

    return candidates


def _extract_ner_from_text(
    text: str,
    *,
    source: str,
    record_id: str,
) -> list[EntityCandidate]:
    if not text or not text.strip():
        return []

    candidates: list[EntityCandidate] = []
    for span in extract_ner_spans(text):
        fields = ner_span_to_candidate_fields(span)
        candidates.append(
            EntityCandidate(
                entity_type=fields["entity_type"],
                value=fields["value"],
                normalized_value=fields["normalized_value"],
                confidence=fields["confidence"],
                source=source,
                record_id=record_id,
                start=fields["start"],
                end=fields["end"],
                offset=fields["offset"],
                source_text=fields["source_text"],
                extraction_method=fields["extraction_method"],
                resolution_eligible=fields["resolution_eligible"],
            )
        )
    return candidates


def merge_extraction_candidates(
    regex_candidates: list[EntityCandidate],
    ner_candidates: list[EntityCandidate],
) -> list[EntityCandidate]:
    """Fuse regex and NER candidates, preferring deterministic identifiers on overlap."""
    merged = list(regex_candidates)
    for ner in ner_candidates:
        if any(
            _spans_overlap(ner["start"], ner["end"], regex["start"], regex["end"])
            and regex["entity_type"] in IDENTIFIER_ENTITY_TYPES
            for regex in regex_candidates
        ):
            continue
        merged.append(ner)
    return merged


def extract_from_text(
    text: str,
    *,
    source: str,
    record_id: str,
    field: str | None = None,
    include_ner: bool = True,
    prose_mode: bool | None = None,
) -> list[EntityCandidate]:
    """Scan one text field and return regex + optional NER candidates."""
    active_prose_mode = prose_mode if prose_mode is not None else field == UNSTRUCTURED_TEXT_FIELD
    regex_candidates = _extract_regex_from_text(
        text,
        source=source,
        record_id=record_id,
        field=field,
        prose_mode=active_prose_mode,
    )
    if not include_ner:
        return regex_candidates

    ner_candidates = _extract_ner_from_text(
        text,
        source=source,
        record_id=record_id,
    )
    return merge_extraction_candidates(regex_candidates, ner_candidates)


def _field_to_text(value: Any, *, preserve_exact: bool = False) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    if preserve_exact:
        return value if value else None
    text = value.strip()
    return text if text else None


def extract_from_record(
    record: NormalizedRecord,
    *,
    include_ner: bool = True,
) -> list[EntityCandidate]:
    """Extract entity candidates from every textual field in one record."""
    candidates: list[EntityCandidate] = []
    source = record["source"]
    record_id = record["record_id"]

    for field, value in record["data"].items():
        if field in PROVENANCE_DATA_FIELDS:
            continue

        text = _field_to_text(value, preserve_exact=field == UNSTRUCTURED_TEXT_FIELD)
        if text is None:
            continue

        candidates.extend(
            extract_from_text(
                text,
                source=source,
                record_id=record_id,
                field=field,
                include_ner=include_ner,
                prose_mode=field == UNSTRUCTURED_TEXT_FIELD,
            )
        )

    return candidates


def extract_from_records(
    records: list[NormalizedRecord],
    *,
    include_ner: bool = True,
) -> list[EntityCandidate]:
    """Extract entity candidates from a batch of normalized records."""
    candidates: list[EntityCandidate] = []

    for record in records:
        candidates.extend(extract_from_record(record, include_ner=include_ner))

    return candidates
