"""Unified regex + NER extraction tests for unstructured FIR prose."""

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.extraction_config import (  # noqa: E402
    CONFIDENCE_REGEX,
    EXTRACTION_METHOD_NER,
    EXTRACTION_METHOD_REGEX,
    NER_MIN_RESOLUTION_CONFIDENCE,
)
from app.services.fir_ner_fallback import RuleBasedFirNerExtractor  # noqa: E402
from app.services.ner_extraction import NerSpan, set_ner_extractor  # noqa: E402
from app.services.unstructured_extraction import (  # noqa: E402
    extract_from_unstructured_record,
    extract_unified_from_unstructured_record,
)
from app.services.unstructured_ingestion import ingest_unstructured_fir  # noqa: E402

FIXED_TIME = "2026-01-01T00:00:00+00:00"

FIR_NARRATIVE = (
    "FIR DEL/2026/0042 dated 08-09-2026. Complainant Priya Verma met Rahul Sharma "
    "near Sector 21 Bus Stand in Mumbai. The Delhi Police registered a robbery event "
    "after Acme Logistics was named. Suspect phone +91-90000-10001 and vehicle DL11AB1001."
)


class StaticNerExtractor:
    def __init__(self, spans: list[NerSpan]):
        self.spans = spans

    def extract(self, text: str) -> list[NerSpan]:
        return [
            span
            for span in self.spans
            if 0 <= span.start < span.end <= len(text)
            and text[span.start : span.end] == span.source_text
        ]


def _ingest(text: str = FIR_NARRATIVE) -> dict:
    return ingest_unstructured_fir(
        {
            "source": "unstructured_fir",
            "source_ref": "FIR-DEL-2026-0042",
            "jurisdiction": "DEL",
            "text": text,
        },
        ingested_at=FIXED_TIME,
    )


class UnstructuredNerFusionTests(unittest.TestCase):
    def setUp(self):
        text = FIR_NARRATIVE
        self.spans = [
            NerSpan("person", text[52:63], 0.97, 52, 63, text[52:63]),
            NerSpan("person", text[68:80], 0.96, 68, 80, text[68:80]),
            NerSpan("location", text[86:105], 0.91, 86, 105, text[86:105]),
            NerSpan("location", text[109:115], 0.90, 109, 115, text[109:115]),
            NerSpan("organisation", text[121:133], 0.84, 121, 133, text[121:133]),
            NerSpan("organisation", text[167:181], 0.82, 167, 181, text[167:181]),
            NerSpan("event", text[147:160], 0.80, 147, 160, text[147:160]),
        ]
        set_ner_extractor(StaticNerExtractor(self.spans))
        self.record = _ingest(text)

    def tearDown(self):
        set_ner_extractor(None)

    def test_ner_extracts_supported_entity_types(self):
        candidates = extract_unified_from_unstructured_record(self.record)
        types = {candidate["entity_type"] for candidate in candidates}

        self.assertTrue({"person", "location", "organisation", "event"}.issubset(types))

    def test_ner_offsets_reference_original_text(self):
        text = self.record["data"]["text"]
        candidates = extract_unified_from_unstructured_record(self.record)
        ner_candidates = [
            candidate for candidate in candidates if candidate["extraction_method"] == "ner"
        ]

        self.assertTrue(ner_candidates)
        for candidate in ner_candidates:
            self.assertEqual(text[candidate["start"] : candidate["end"]], candidate["source_text"])
            self.assertEqual(text[candidate["start"] : candidate["end"]], candidate["value"])

    def test_ner_confidence_is_preserved(self):
        candidates = extract_unified_from_unstructured_record(self.record)
        person = next(
            candidate
            for candidate in candidates
            if candidate["entity_type"] == "person"
            and candidate["extraction_method"] == "ner"
        )
        self.assertEqual(person["confidence"], 0.97)

    def test_extraction_method_distinguishes_regex_and_ner(self):
        candidates = extract_unified_from_unstructured_record(self.record)
        methods = {candidate["extraction_method"] for candidate in candidates}

        self.assertIn(EXTRACTION_METHOD_REGEX, methods)
        self.assertIn(EXTRACTION_METHOD_NER, methods)

        phone = next(item for item in candidates if item["entity_type"] == "phone")
        self.assertEqual(phone["extraction_method"], EXTRACTION_METHOD_REGEX)
        self.assertEqual(phone["confidence"], CONFIDENCE_REGEX)

    def test_regex_identifiers_still_work_with_ner_enabled(self):
        candidates = extract_unified_from_unstructured_record(self.record)
        normalized = {
            candidate["entity_type"]: candidate["normalized_value"]
            for candidate in candidates
            if candidate["extraction_method"] == EXTRACTION_METHOD_REGEX
        }

        self.assertEqual(normalized["phone"], "+919000010001")
        self.assertEqual(normalized["vehicle"], "DL11AB1001")

    def test_regex_and_ner_candidates_coexist(self):
        regex_only = extract_from_unstructured_record(self.record, include_ner=False)
        unified = extract_unified_from_unstructured_record(self.record)

        self.assertGreater(len(unified), len(regex_only))
        self.assertTrue(any(item["extraction_method"] == "ner" for item in unified))


class FallbackFirNerTests(unittest.TestCase):
    def setUp(self):
        set_ner_extractor(RuleBasedFirNerExtractor())

    def tearDown(self):
        set_ner_extractor(None)

    def test_fallback_extracts_fir_entities_deterministically(self):
        text = (
            "FIR DEL/2026/0099 dated 08-09-2026. Complainant Priya Verma was seen in Mumbai. "
            "Delhi Police registered a cyber crime."
        )
        record = _ingest(text)
        candidates = extract_unified_from_unstructured_record(record)
        types = {candidate["entity_type"] for candidate in candidates}

        self.assertIn("person", types)
        self.assertIn("location", types)
        self.assertIn("organisation", types)
        self.assertIn("event", types)

    def test_low_confidence_fallback_organisation_is_not_resolution_eligible(self):
        text = "Acme Logistics was named in the narrative."
        record = _ingest(text)
        candidates = extract_unified_from_unstructured_record(record)
        org = next(item for item in candidates if item["entity_type"] == "organisation")

        self.assertLess(org["confidence"], NER_MIN_RESOLUTION_CONFIDENCE)
        self.assertFalse(org["resolution_eligible"])


if __name__ == "__main__":
    unittest.main()
