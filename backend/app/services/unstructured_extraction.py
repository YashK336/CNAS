"""Unified regex + NER extraction from unstructured FIR prose."""

from __future__ import annotations

from app.services.extraction import (
    UNSTRUCTURED_TEXT_FIELD,
    EntityCandidate,
    extract_from_text,
    merge_extraction_candidates,
)
from app.services.normalization import NormalizedRecord
from app.services.ner_extraction import extract_ner_spans, ner_span_to_candidate_fields


def _ner_candidates_from_text(
    text: str,
    *,
    source: str,
    record_id: str,
) -> list[EntityCandidate]:
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


def extract_from_unstructured_record(
    record: NormalizedRecord,
    *,
    include_ner: bool = False,
) -> list[EntityCandidate]:
    """Extract regex identifier candidates from one unstructured FIR NormalizedRecord."""
    text = record["data"].get(UNSTRUCTURED_TEXT_FIELD)
    if not isinstance(text, str) or not text:
        return []

    return extract_from_text(
        text,
        source=record["source"],
        record_id=record["record_id"],
        field=UNSTRUCTURED_TEXT_FIELD,
        include_ner=include_ner,
        prose_mode=True,
    )


def extract_unified_from_unstructured_record(
    record: NormalizedRecord,
    *,
    include_ner: bool = True,
) -> list[EntityCandidate]:
    """Regex + NER extraction with fusion for unstructured FIR prose."""
    text = record["data"].get(UNSTRUCTURED_TEXT_FIELD)
    if not isinstance(text, str) or not text:
        return []

    regex_candidates = extract_from_text(
        text,
        source=record["source"],
        record_id=record["record_id"],
        field=UNSTRUCTURED_TEXT_FIELD,
        include_ner=False,
        prose_mode=True,
    )
    if not include_ner:
        return regex_candidates

    ner_candidates = _ner_candidates_from_text(
        text,
        source=record["source"],
        record_id=record["record_id"],
    )
    return merge_extraction_candidates(regex_candidates, ner_candidates)
