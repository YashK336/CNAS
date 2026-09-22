"""Thresholds and constants for CNAS Layer 2 entity extraction."""

from __future__ import annotations

EXTRACTION_METHOD_REGEX = "regex"
EXTRACTION_METHOD_NER = "ner"

CONFIDENCE_REGEX = 1.0

# Minimum NER confidence required before a candidate may enter resolution/graph paths.
NER_MIN_RESOLUTION_CONFIDENCE = 0.85

SPACY_MODEL_NAME = "en_core_web_trf"

# spaCy label -> CNAS NER entity type
SPACY_LABEL_TO_ENTITY_TYPE: dict[str, str] = {
    "PERSON": "person",
    "ORG": "organisation",
    "GPE": "location",
    "LOC": "location",
    "FAC": "location",
    "EVENT": "event",
}

NER_ENTITY_TYPES = frozenset({"person", "location", "organisation", "event"})

# Deterministic base confidence by spaCy label (reproducible scoring layer).
SPACY_LABEL_BASE_CONFIDENCE: dict[str, float] = {
    "PERSON": 0.97,
    "ORG": 0.93,
    "GPE": 0.91,
    "LOC": 0.91,
    "FAC": 0.88,
    "EVENT": 0.86,
}

# Explicit fallback confidence for rule-based FIR NER (below spaCy, above noise).
FALLBACK_NER_CONFIDENCE: dict[str, float] = {
    "person": 0.88,
    "location": 0.86,
    "organisation": 0.84,
    "event": 0.82,
}
