"""Deterministic rule-based NER fallback for unstructured FIR prose."""

from __future__ import annotations

import re

from app.services.extraction_config import FALLBACK_NER_CONFIDENCE
from app.services.ner_extraction import NerSpan

PERSON_ROLE_PATTERN = re.compile(
    r"\b(?:Complainant|Accused|Witness|Suspect|named|states\s+that)\s+"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
)
LOCATION_CONTEXT_PATTERN = re.compile(
    r"\b(?:in|at|near|from)\s+"
    r"([A-Z][A-Za-z0-9][A-Za-z0-9\s\-]{1,38}[A-Za-z0-9])",
)
ORGANISATION_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+"
    r"(?:Police|Logistics|Bank|Corporation|Ltd\.?|Limited))\b",
)
EVENT_PATTERN = re.compile(
    r"\b("
    r"robbery(?:\s+event)?|"
    r"cyber crime|"
    r"organized crime|"
    r"organised crime|"
    r"theft|"
    r"fraud|"
    r"murder|"
    r"assault|"
    r"extortion"
    r")\b",
    re.IGNORECASE,
)
FIR_REFERENCE_PATTERN = re.compile(
    r"\b("
    r"FIR(?:\sNO\.?|\s|/|-)\s*[A-Z]{0,3}[\s/\-]*\d{4}[\s/\-]*\d+|"
    r"FIR\d{5,}"
    r")\b",
    re.IGNORECASE,
)


def _append_span(
    spans: list[NerSpan],
    *,
    entity_type: str,
    text: str,
    start: int,
    end: int,
) -> None:
    source_text = text[start:end]
    if not source_text.strip():
        return

    for existing in spans:
        if existing.start == start and existing.end == end and existing.entity_type == entity_type:
            return

    normalized = source_text.strip()
    spans.append(
        NerSpan(
            entity_type=entity_type,
            value=source_text,
            confidence=FALLBACK_NER_CONFIDENCE[entity_type],
            start=start,
            end=end,
            source_text=source_text,
        )
    )


class RuleBasedFirNerExtractor:
    """Lightweight deterministic NER when spaCy is unavailable."""

    def extract(self, text: str) -> list[NerSpan]:
        if not text or not text.strip():
            return []

        spans: list[NerSpan] = []

        for match in PERSON_ROLE_PATTERN.finditer(text):
            start = match.start(1)
            end = match.end(1)
            _append_span(spans, entity_type="person", text=text, start=start, end=end)

        for match in LOCATION_CONTEXT_PATTERN.finditer(text):
            start = match.start(1)
            end = match.end(1)
            _append_span(spans, entity_type="location", text=text, start=start, end=end)

        for match in ORGANISATION_PATTERN.finditer(text):
            start = match.start(1)
            end = match.end(1)
            _append_span(spans, entity_type="organisation", text=text, start=start, end=end)

        for match in EVENT_PATTERN.finditer(text):
            start = match.start(1)
            end = match.end(1)
            _append_span(spans, entity_type="event", text=text, start=start, end=end)

        for match in FIR_REFERENCE_PATTERN.finditer(text):
            start = match.start(1)
            end = match.end(1)
            _append_span(spans, entity_type="event", text=text, start=start, end=end)

        return spans
