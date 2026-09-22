"""spaCy transformer NER for CNAS Layer 2 extraction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.services.extraction_config import (
    EXTRACTION_METHOD_NER,
    NER_MIN_RESOLUTION_CONFIDENCE,
    SPACY_LABEL_BASE_CONFIDENCE,
    SPACY_LABEL_TO_ENTITY_TYPE,
    SPACY_MODEL_NAME,
)

_extractor: "NerExtractor | None" = None


@dataclass(frozen=True)
class NerSpan:
    entity_type: str
    value: str
    confidence: float
    start: int
    end: int
    source_text: str


class NerExtractor(Protocol):
    def extract(self, text: str) -> list[NerSpan]: ...


class SpacyTransformerNerExtractor:
    """Transformer-based NER using the pinned spaCy pipeline."""

    def __init__(self, model_name: str = SPACY_MODEL_NAME) -> None:
        self.model_name = model_name
        self._nlp = None

    def _load(self):
        if self._nlp is None:
            import spacy

            self._nlp = spacy.load(self.model_name, disable=["lemmatizer"])
        return self._nlp

    def extract(self, text: str) -> list[NerSpan]:
        if not text or not text.strip():
            return []

        doc = self._load()(text)
        spans: list[NerSpan] = []

        for ent in doc.ents:
            entity_type = SPACY_LABEL_TO_ENTITY_TYPE.get(ent.label_)
            if entity_type is None:
                continue

            source_text = text[ent.start_char : ent.end_char]
            if not source_text.strip():
                continue

            confidence = deterministic_ner_confidence(
                spacy_label=ent.label_,
                start=ent.start_char,
                end=ent.end_char,
            )
            spans.append(
                NerSpan(
                    entity_type=entity_type,
                    value=source_text,
                    confidence=confidence,
                    start=ent.start_char,
                    end=ent.end_char,
                    source_text=source_text,
                )
            )

        return spans


class PluggableFirNerExtractor:
    """Try spaCy when available; otherwise use deterministic FIR rule fallback."""

    def __init__(self) -> None:
        self._primary: NerExtractor | None = None
        self._fallback: NerExtractor | None = None
        self._use_fallback = False

    def _fallback_extractor(self) -> NerExtractor:
        if self._fallback is None:
            from app.services.fir_ner_fallback import RuleBasedFirNerExtractor

            self._fallback = RuleBasedFirNerExtractor()
        return self._fallback

    def extract(self, text: str) -> list[NerSpan]:
        if self._use_fallback:
            return self._fallback_extractor().extract(text)

        try:
            if self._primary is None:
                self._primary = SpacyTransformerNerExtractor()
            return self._primary.extract(text)
        except Exception:
            self._use_fallback = True
            return self._fallback_extractor().extract(text)


def deterministic_ner_confidence(*, spacy_label: str, start: int, end: int) -> float:
    """Return a reproducible confidence score for a spaCy entity span."""
    base = SPACY_LABEL_BASE_CONFIDENCE.get(spacy_label, 0.85)
    span_len = max(end - start, 0)
    penalty = 0.02 if span_len <= 3 else 0.0
    return round(max(0.0, min(1.0, base - penalty)), 4)


def resolution_eligible(confidence: float) -> bool:
    return confidence >= NER_MIN_RESOLUTION_CONFIDENCE


def set_ner_extractor(extractor: NerExtractor | None) -> None:
    global _extractor
    _extractor = extractor


def get_ner_extractor() -> NerExtractor:
    global _extractor
    if _extractor is None:
        _extractor = PluggableFirNerExtractor()
    return _extractor


def extract_ner_spans(text: str) -> list[NerSpan]:
    return get_ner_extractor().extract(text)


def ner_normalized_value(span: NerSpan) -> str:
    return span.source_text.strip()


def ner_span_to_candidate_fields(span: NerSpan) -> dict:
    normalized = ner_normalized_value(span)
    return {
        "entity_type": span.entity_type,
        "value": span.source_text,
        "normalized_value": normalized,
        "confidence": span.confidence,
        "start": span.start,
        "end": span.end,
        "offset": span.start,
        "source_text": span.source_text,
        "extraction_method": EXTRACTION_METHOD_NER,
        "resolution_eligible": resolution_eligible(span.confidence),
    }
