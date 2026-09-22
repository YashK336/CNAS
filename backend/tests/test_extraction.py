"""Deterministic entity extraction tests."""

import sys
import unittest
from pathlib import Path

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.extraction import (  # noqa: E402
    extract_from_record,
    extract_from_records,
    extract_from_text,
    normalize_bank_account,
    normalize_ifsc,
    normalize_phone,
    normalize_vehicle,
)
from app.services.normalization import normalize_row  # noqa: E402


class NormalizationTests(unittest.TestCase):
    def test_phone_normalization(self):
        self.assertEqual(normalize_phone("+91-90000-10001"), "+919000010001")
        self.assertEqual(normalize_phone("+91 9000010001"), "+919000010001")
        self.assertEqual(normalize_phone("9000010001"), "+919000010001")

    def test_vehicle_normalization(self):
        self.assertEqual(normalize_vehicle("dl11ab1001"), "DL11AB1001")

    def test_bank_account_normalization(self):
        self.assertEqual(normalize_bank_account("acc100001"), "ACC100001")

    def test_ifsc_normalization(self):
        self.assertEqual(normalize_ifsc("hdfc0001234"), "HDFC0001234")


class PhoneExtractionTests(unittest.TestCase):
    def test_valid_phone(self):
        matches = extract_from_text(
            "Contact +91-90000-10001 for details",
            source="persons",
            record_id="persons:P001",
            include_ner=False,
        )
        phones = [m for m in matches if m["entity_type"] == "phone"]

        self.assertEqual(len(phones), 1)
        self.assertEqual(phones[0]["value"], "+91-90000-10001")
        self.assertEqual(phones[0]["normalized_value"], "+919000010001")
        self.assertEqual(phones[0]["confidence"], 1.0)
        self.assertEqual(phones[0]["offset"], 8)

    def test_invalid_phone_text(self):
        matches = extract_from_text(
            "No contact information here",
            source="persons",
            record_id="persons:P999",
            include_ner=False,
        )
        self.assertEqual(matches, [])

    def test_multiple_phones(self):
        text = "Phones +91-90000-10001 and +91-90000-10002"
        matches = extract_from_text(
            text,
            source="cdr",
            record_id="cdr:row:0",
            include_ner=False,
        )
        phones = [m for m in matches if m["entity_type"] == "phone"]

        self.assertEqual(len(phones), 2)
        self.assertEqual(phones[0]["offset"], 7)
        self.assertEqual(phones[1]["offset"], 27)
        self.assertEqual(phones[0]["normalized_value"], "+919000010001")
        self.assertEqual(phones[1]["normalized_value"], "+919000010002")


class VehicleExtractionTests(unittest.TestCase):
    def test_valid_vehicle(self):
        matches = extract_from_text(
            "Vehicle DL11AB1001 seen near toll",
            source="vehicles",
            record_id="vehicles:DL11AB1001",
            include_ner=False,
        )
        vehicles = [m for m in matches if m["entity_type"] == "vehicle"]

        self.assertEqual(len(vehicles), 1)
        self.assertEqual(vehicles[0]["value"], "DL11AB1001")
        self.assertEqual(vehicles[0]["normalized_value"], "DL11AB1001")
        self.assertEqual(vehicles[0]["offset"], 8)

    def test_invalid_vehicle_text(self):
        matches = extract_from_text(
            "Plate XX1AB100 is incomplete",
            source="vehicles",
            record_id="vehicles:row:0",
            include_ner=False,
        )
        vehicles = [m for m in matches if m["entity_type"] == "vehicle"]
        self.assertEqual(vehicles, [])


class BankExtractionTests(unittest.TestCase):
    def test_valid_bank_account_token(self):
        matches = extract_from_text(
            "Transfer to ACC100004 completed",
            source="finance",
            record_id="finance:row:0",
            field="note",
            include_ner=False,
        )
        accounts = [m for m in matches if m["entity_type"] == "bank_account"]

        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]["value"], "ACC100004")
        self.assertEqual(accounts[0]["normalized_value"], "ACC100004")

    def test_numeric_account_only_in_account_fields(self):
        numeric = "123456789012"
        from_field = extract_from_text(
            numeric,
            source="finance",
            record_id="finance:row:0",
            field="sender_account",
            include_ner=False,
        )
        from_other = extract_from_text(
            numeric,
            source="finance",
            record_id="finance:row:0",
            field="amount",
            include_ner=False,
        )

        self.assertEqual(len(from_field), 1)
        self.assertEqual(from_field[0]["value"], numeric)
        self.assertEqual(from_field[0]["normalized_value"], numeric)
        self.assertEqual(from_other, [])


class IfscExtractionTests(unittest.TestCase):
    def test_valid_ifsc(self):
        matches = extract_from_text(
            "Paid via HDFC0001234 branch",
            source="finance",
            record_id="finance:row:0",
            include_ner=False,
        )
        codes = [m for m in matches if m["entity_type"] == "ifsc"]

        self.assertEqual(len(codes), 1)
        self.assertEqual(codes[0]["value"], "HDFC0001234")
        self.assertEqual(codes[0]["normalized_value"], "HDFC0001234")
        self.assertEqual(codes[0]["offset"], 9)

    def test_invalid_ifsc(self):
        matches = extract_from_text(
            "Code HDFC001234 is not valid IFSC",
            source="finance",
            record_id="finance:row:0",
            include_ner=False,
        )
        codes = [m for m in matches if m["entity_type"] == "ifsc"]
        self.assertEqual(codes, [])


class RecordExtractionTests(unittest.TestCase):
    def test_extract_from_normalized_person_record(self):
        row = pd.Series(
            {
                "person_id": "P001",
                "name": "Rajesh Kumar",
                "phone": "+91-90000-10001",
                "vehicle_no": "DL11AB1001",
                "bank_account": "ACC100001",
                "social_id": "user_001",
                "home_city": "Mumbai",
                "risk_group": "high",
            }
        )
        record = normalize_row("persons", row, 0, ingested_at="2026-01-01T00:00:00+00:00")
        candidates = extract_from_record(record, include_ner=False)

        by_type = {}
        for candidate in candidates:
            by_type.setdefault(candidate["entity_type"], []).append(
                candidate["normalized_value"]
            )

        self.assertEqual(by_type["phone"], ["+919000010001"])
        self.assertEqual(by_type["vehicle"], ["DL11AB1001"])
        self.assertEqual(by_type["bank_account"], ["ACC100001"])
        self.assertTrue(all(c["source"] == "persons" for c in candidates))
        self.assertTrue(all(c["record_id"] == "persons:P001" for c in candidates))

    def test_extract_from_records_batch(self):
        row = pd.Series({"person_id": "P002", "phone": "+91-90000-10002"})
        records = [
            normalize_row("persons", row, 0, ingested_at="2026-01-01T00:00:00+00:00"),
            normalize_row("persons", row, 1, ingested_at="2026-01-01T00:00:00+00:00"),
        ]

        candidates = extract_from_records(records, include_ner=False)
        phones = [c for c in candidates if c["entity_type"] == "phone"]

        self.assertEqual(len(phones), 2)


if __name__ == "__main__":
    unittest.main()
