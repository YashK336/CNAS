"""Deterministic extraction tests for unstructured FIR prose."""

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.extraction import extract_from_record  # noqa: E402
from app.services.unstructured_extraction import extract_from_unstructured_record  # noqa: E402
from app.services.unstructured_ingestion import ingest_unstructured_fir  # noqa: E402

FIXED_TIME = "2026-01-01T00:00:00+00:00"

FIR_PROSE = (
    "FIR DEL/2026/0042 dated 08-09-2026. Complainant states accused used phone "
    "+91-90000-10001, vehicle DL11AB1001, bank account ACC100004, and IFSC HDFC0001234. "
    "Funds were transferred from account 123456789012."
)


def _ingest(text: str = FIR_PROSE) -> dict:
    return ingest_unstructured_fir(
        {
            "source": "unstructured_fir",
            "source_ref": "FIR-DEL-2026-0042",
            "jurisdiction": "DEL",
            "text": text,
        },
        ingested_at=FIXED_TIME,
    )


class UnstructuredProseExtractionTests(unittest.TestCase):
    def setUp(self):
        self.record = _ingest()

    def test_extracts_phone_vehicle_account_and_ifsc_from_prose(self):
        candidates = extract_from_unstructured_record(self.record)

        by_type = {}
        for candidate in candidates:
            by_type.setdefault(candidate["entity_type"], []).append(candidate)

        self.assertIn("phone", by_type)
        self.assertIn("vehicle", by_type)
        self.assertIn("bank_account", by_type)
        self.assertIn("ifsc", by_type)
        self.assertEqual(by_type["phone"][0]["normalized_value"], "+919000010001")
        self.assertEqual(by_type["vehicle"][0]["normalized_value"], "DL11AB1001")
        self.assertEqual(by_type["ifsc"][0]["normalized_value"], "HDFC0001234")

    def test_extracts_multiple_entities(self):
        text = (
            "Suspect contacted +91-90000-10001 and +91-90000-10002 using vehicles "
            "DL11AB1001 and KA12AB1002."
        )
        record = _ingest(text)
        candidates = extract_from_unstructured_record(record)

        phones = [item for item in candidates if item["entity_type"] == "phone"]
        vehicles = [item for item in candidates if item["entity_type"] == "vehicle"]

        self.assertEqual(len(phones), 2)
        self.assertEqual(len(vehicles), 2)

    def test_offsets_reference_exact_substrings(self):
        text = self.record["data"]["text"]
        candidates = extract_from_unstructured_record(self.record)

        for candidate in candidates:
            substring = text[candidate["start"] : candidate["end"]]
            self.assertEqual(substring, candidate["value"])
            self.assertEqual(substring, candidate["source_text"])

    def test_raw_and_normalized_values_are_preserved(self):
        candidates = extract_from_unstructured_record(self.record)
        phone = next(item for item in candidates if item["entity_type"] == "phone")

        self.assertEqual(phone["value"], "+91-90000-10001")
        self.assertEqual(phone["normalized_value"], "+919000010001")
        self.assertEqual(phone["source_text"], "+91-90000-10001")

    def test_provenance_is_preserved(self):
        candidates = extract_from_unstructured_record(self.record)

        self.assertTrue(candidates)
        for candidate in candidates:
            self.assertEqual(candidate["source"], "unstructured_fir")
            self.assertEqual(candidate["record_id"], "unstructured_fir:FIR-DEL-2026-0042")

    def test_results_are_deterministic(self):
        first = extract_from_unstructured_record(self.record)
        second = extract_from_unstructured_record(self.record)

        self.assertEqual(first, second)

    def test_extract_from_record_skips_provenance_fields(self):
        candidates = extract_from_record(self.record, include_ner=False)
        types = {candidate["entity_type"] for candidate in candidates}

        self.assertIn("phone", types)
        self.assertNotIn("source_ref", types)
        self.assertNotIn("jurisdiction", types)


class UnstructuredFalsePositiveTests(unittest.TestCase):
    def test_case_reference_number_is_not_treated_as_phone(self):
        text = "Case No. 9876543210 was registered on 08-09-2026 for FIR DEL/2026/0042."
        record = _ingest(text)
        candidates = extract_from_unstructured_record(record)
        phones = [item for item in candidates if item["entity_type"] == "phone"]

        self.assertEqual(phones, [])

    def test_bare_numeric_account_is_not_extracted_without_context(self):
        text = "Reference number 123456789012 appears in the narrative."
        record = _ingest(text)
        candidates = extract_from_unstructured_record(record)
        accounts = [item for item in candidates if item["entity_type"] == "bank_account"]

        self.assertEqual(accounts, [])

    def test_numeric_account_with_context_is_extracted(self):
        text = "Funds were transferred from account 123456789012 to ACC100004."
        record = _ingest(text)
        candidates = extract_from_unstructured_record(record)
        accounts = [
            item["normalized_value"]
            for item in candidates
            if item["entity_type"] == "bank_account"
        ]

        self.assertIn("123456789012", accounts)
        self.assertIn("ACC100004", accounts)


if __name__ == "__main__":
    unittest.main()
