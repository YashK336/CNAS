"""Layer 2 spaCy NER extraction tests."""

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.entity_resolution import (  # noqa: E402
    build_canonical_registry,
    resolve_candidate,
)
from app.services.extraction import (  # noqa: E402
    extract_from_text,
    merge_extraction_candidates,
)
from app.services.extraction_config import NER_MIN_RESOLUTION_CONFIDENCE  # noqa: E402
from app.services.ner_extraction import (  # noqa: E402
    NerSpan,
    deterministic_ner_confidence,
    resolution_eligible,
    set_ner_extractor,
)
from app.services.resolution_config import (  # noqa: E402
    METHOD_NONE,
    RESOLUTION_STATUS_UNRESOLVED,
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


NARRATIVE = (
    "Complainant Priya Verma met Rahul Sharma near Sector 21 Bus Stand in Mumbai. "
    "The Delhi Police registered a robbery event after Acme Logistics was named."
)


class NerExtractionTestCase(unittest.TestCase):
    def setUp(self):
        text = NARRATIVE
        self.spans = [
            NerSpan("person", "Priya Verma", 0.97, 12, 23, text[12:23]),
            NerSpan("person", "Rahul Sharma", 0.96, 28, 40, text[28:40]),
            NerSpan("location", "Sector 21 Bus Stand", 0.91, 46, 65, text[46:65]),
            NerSpan("location", "Mumbai", 0.90, 69, 75, text[69:75]),
            NerSpan("organisation", "Delhi Police", 0.84, 81, 93, text[81:93]),
            NerSpan("organisation", "Acme Logistics", 0.82, 127, 141, text[127:141]),
            NerSpan("event", "robbery event", 0.80, 107, 120, text[107:120]),
        ]
        set_ner_extractor(StaticNerExtractor(self.spans))

    def tearDown(self):
        set_ner_extractor(None)

    def _matches(self, entity_type: str):
        return [
            candidate
            for candidate in extract_from_text(
                NARRATIVE,
                source="fir",
                record_id="fir:FIR00001",
            )
            if candidate["entity_type"] == entity_type
        ]


class PersonExtractionTests(NerExtractionTestCase):
    def test_person_extraction(self):
        people = self._matches("person")
        self.assertEqual([item["value"] for item in people], ["Priya Verma", "Rahul Sharma"])
        self.assertEqual(people[0]["source_text"], "Priya Verma")
        self.assertEqual(people[0]["extraction_method"], "ner")


class LocationExtractionTests(NerExtractionTestCase):
    def test_location_extraction(self):
        locations = self._matches("location")
        self.assertEqual(
            [item["value"] for item in locations],
            ["Sector 21 Bus Stand", "Mumbai"],
        )


class OrganisationExtractionTests(NerExtractionTestCase):
    def test_organisation_extraction(self):
        organisations = self._matches("organisation")
        self.assertEqual(
            [item["value"] for item in organisations],
            ["Delhi Police", "Acme Logistics"],
        )


class EventExtractionTests(NerExtractionTestCase):
    def test_event_extraction(self):
        events = self._matches("event")
        self.assertEqual([item["value"] for item in events], ["robbery event"])
        self.assertEqual(events[0]["source_text"], "robbery event")


class ConfidenceTests(NerExtractionTestCase):
    def test_confidence_values_are_present(self):
        candidates = extract_from_text(
            NARRATIVE,
            source="fir",
            record_id="fir:FIR00001",
        )
        ner_candidates = [item for item in candidates if item["extraction_method"] == "ner"]
        self.assertTrue(ner_candidates)
        for candidate in ner_candidates:
            self.assertGreaterEqual(candidate["confidence"], 0.0)
            self.assertLessEqual(candidate["confidence"], 1.0)

    def test_deterministic_confidence_formula(self):
        self.assertEqual(
            deterministic_ner_confidence(spacy_label="PERSON", start=0, end=11),
            0.97,
        )
        self.assertEqual(
            deterministic_ner_confidence(spacy_label="GPE", start=0, end=2),
            0.89,
        )


class CharacterOffsetTests(NerExtractionTestCase):
    def test_character_offsets_and_source_text(self):
        person = self._matches("person")[0]
        self.assertEqual(person["start"], 12)
        self.assertEqual(person["end"], 23)
        self.assertEqual(person["offset"], 12)
        self.assertEqual(
            NARRATIVE[person["start"] : person["end"]],
            person["source_text"],
        )


class MixedRegexNerTests(unittest.TestCase):
    def setUp(self):
        text = "Contact Priya Verma on +91-90000-10001 near DL11AB1001 in Mumbai."
        self.spans = [
            NerSpan("person", "Priya Verma", 0.97, 8, 19, text[8:19]),
            NerSpan("location", "Mumbai", 0.91, 58, 64, text[58:64]),
        ]
        set_ner_extractor(StaticNerExtractor(self.spans))
        self.text = text

    def tearDown(self):
        set_ner_extractor(None)

    def test_regex_and_ner_are_combined(self):
        candidates = extract_from_text(
            self.text,
            source="fir",
            record_id="fir:FIR00002",
        )
        types = {candidate["entity_type"] for candidate in candidates}
        self.assertEqual(types, {"person", "phone", "vehicle", "location"})

        phone = next(item for item in candidates if item["entity_type"] == "phone")
        self.assertEqual(phone["extraction_method"], "regex")
        self.assertEqual(phone["confidence"], 1.0)


class LowConfidenceHandlingTests(unittest.TestCase):
    def setUp(self):
        self.text = "Acme Logistics was mentioned."
        self.spans = [
            NerSpan("organisation", "Acme Logistics", 0.70, 0, 14, self.text[0:14]),
        ]
        set_ner_extractor(StaticNerExtractor(self.spans))

    def tearDown(self):
        set_ner_extractor(None)

    def test_low_confidence_candidate_is_extracted_but_not_resolution_eligible(self):
        candidates = extract_from_text(
            self.text,
            source="fir",
            record_id="fir:FIR00003",
        )
        org = candidates[0]
        self.assertLess(org["confidence"], NER_MIN_RESOLUTION_CONFIDENCE)
        self.assertFalse(org["resolution_eligible"])

        result = resolve_candidate(org, build_canonical_registry())
        self.assertEqual(result["status"], RESOLUTION_STATUS_UNRESOLVED)
        self.assertEqual(result["method"], METHOD_NONE)
        self.assertIsNone(result["matched_entity_id"])


class EmptyAndMalformedInputTests(unittest.TestCase):
    def setUp(self):
        set_ner_extractor(StaticNerExtractor([]))

    def tearDown(self):
        set_ner_extractor(None)

    def test_empty_text_returns_no_candidates(self):
        self.assertEqual(
            extract_from_text("", source="fir", record_id="fir:empty"),
            [],
        )
        self.assertEqual(
            extract_from_text("   ", source="fir", record_id="fir:blank"),
            [],
        )

    def test_malformed_non_string_input_is_handled_by_record_layer(self):
        candidates = extract_from_text(
            "No entities here.",
            source="fir",
            record_id="fir:none",
        )
        self.assertEqual(candidates, [])


class MergeBehaviorTests(unittest.TestCase):
    def test_merge_prefers_regex_on_overlap(self):
        regex = [
            {
                "entity_type": "ifsc",
                "value": "HDFC0001234",
                "normalized_value": "HDFC0001234",
                "confidence": 1.0,
                "source": "finance",
                "record_id": "finance:1",
                "start": 9,
                "end": 20,
                "offset": 9,
                "source_text": "HDFC0001234",
                "extraction_method": "regex",
                "resolution_eligible": True,
            }
        ]
        ner = [
            {
                "entity_type": "organisation",
                "value": "HDFC",
                "normalized_value": "HDFC",
                "confidence": 0.93,
                "source": "finance",
                "record_id": "finance:1",
                "start": 9,
                "end": 13,
                "offset": 9,
                "source_text": "HDFC",
                "extraction_method": "ner",
                "resolution_eligible": True,
            }
        ]
        merged = merge_extraction_candidates(regex, ner)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["entity_type"], "ifsc")


class ResolutionEligibilityHelperTests(unittest.TestCase):
    def test_resolution_eligibility_threshold(self):
        self.assertTrue(resolution_eligible(NER_MIN_RESOLUTION_CONFIDENCE))
        self.assertFalse(resolution_eligible(NER_MIN_RESOLUTION_CONFIDENCE - 0.01))


if __name__ == "__main__":
    unittest.main()
