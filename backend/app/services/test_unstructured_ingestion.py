"""Tests for unstructured FIR/intelligence ingestion contract."""

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.unstructured_ingestion import (  # noqa: E402
    UnstructuredIngestionValidationError,
    build_unstructured_data,
    ingest_unstructured_fir,
)
from app.services.normalization import hash_record_content  # noqa: E402

FIXED_TIME = "2026-01-01T00:00:00+00:00"

SAMPLE_PAYLOAD = {
    "source": "unstructured_fir",
    "source_ref": "FIR-DEL-2026-0042",
    "jurisdiction": "DEL",
    "text": " Complainant reports fraud involving phone +91-90000-10001 and vehicle DL11AB1001.",
    "metadata": {"channel": "police_portal", "language": "en"},
}


class UnstructuredIngestionTests(unittest.TestCase):
    def test_valid_fir_text_creates_normalized_record(self):
        record = ingest_unstructured_fir(
            SAMPLE_PAYLOAD,
            ingested_at=FIXED_TIME,
        )

        self.assertEqual(record["source"], "unstructured_fir")
        self.assertEqual(record["record_id"], "unstructured_fir:FIR-DEL-2026-0042")
        self.assertEqual(record["ingested_at"], FIXED_TIME)
        self.assertEqual(len(record["content_hash"]), 64)
        self.assertEqual(record["data"]["text"], SAMPLE_PAYLOAD["text"])
        self.assertEqual(record["data"]["source_ref"], "FIR-DEL-2026-0042")
        self.assertEqual(record["data"]["jurisdiction"], "DEL")
        self.assertEqual(record["data"]["metadata"]["channel"], "police_portal")

    def test_original_text_is_preserved_exactly(self):
        text_with_whitespace = "  Line one.\n\tPhone +91-90000-10001.\n  "
        record = ingest_unstructured_fir(
            {
                **SAMPLE_PAYLOAD,
                "text": text_with_whitespace,
            },
            ingested_at=FIXED_TIME,
        )

        self.assertEqual(record["data"]["text"], text_with_whitespace)

    def test_same_source_and_content_produces_same_hash(self):
        first = ingest_unstructured_fir(SAMPLE_PAYLOAD, ingested_at=FIXED_TIME)
        second = ingest_unstructured_fir(SAMPLE_PAYLOAD, ingested_at="2026-06-01T00:00:00+00:00")

        self.assertEqual(first["content_hash"], second["content_hash"])

    def test_changing_content_changes_hash(self):
        baseline = ingest_unstructured_fir(SAMPLE_PAYLOAD, ingested_at=FIXED_TIME)
        changed = ingest_unstructured_fir(
            {
                **SAMPLE_PAYLOAD,
                "text": SAMPLE_PAYLOAD["text"] + " Additional witness statement.",
            },
            ingested_at=FIXED_TIME,
        )

        self.assertNotEqual(baseline["content_hash"], changed["content_hash"])

    def test_source_ref_is_preserved(self):
        record = ingest_unstructured_fir(SAMPLE_PAYLOAD, ingested_at=FIXED_TIME)
        self.assertEqual(record["data"]["source_ref"], SAMPLE_PAYLOAD["source_ref"])
        self.assertEqual(record["record_id"], f"{SAMPLE_PAYLOAD['source']}:{SAMPLE_PAYLOAD['source_ref']}")

    def test_jurisdiction_is_preserved(self):
        record = ingest_unstructured_fir(SAMPLE_PAYLOAD, ingested_at=FIXED_TIME)
        self.assertEqual(record["data"]["jurisdiction"], "DEL")

    def test_ingested_at_is_present(self):
        record = ingest_unstructured_fir(SAMPLE_PAYLOAD)
        self.assertTrue(record["ingested_at"])

    def test_hash_uses_existing_normalization_helper(self):
        data = build_unstructured_data(
            text=SAMPLE_PAYLOAD["text"],
            source_ref=SAMPLE_PAYLOAD["source_ref"],
            jurisdiction=SAMPLE_PAYLOAD["jurisdiction"],
            metadata=SAMPLE_PAYLOAD["metadata"],
        )
        record = ingest_unstructured_fir(SAMPLE_PAYLOAD, ingested_at=FIXED_TIME)

        self.assertEqual(
            record["content_hash"],
            hash_record_content(SAMPLE_PAYLOAD["source"], data),
        )


class UnstructuredIngestionValidationTests(unittest.TestCase):
    def test_missing_required_fields_are_rejected(self):
        required_cases = [
            {},
            {"source": "unstructured_fir"},
            {
                "source": "unstructured_fir",
                "source_ref": "FIR-1",
            },
            {
                "source": "unstructured_fir",
                "source_ref": "FIR-1",
                "jurisdiction": "DEL",
            },
        ]

        for payload in required_cases:
            with self.subTest(payload=payload):
                with self.assertRaises(UnstructuredIngestionValidationError):
                    ingest_unstructured_fir(payload)

    def test_empty_required_strings_are_rejected(self):
        for field in ("source", "source_ref", "jurisdiction", "text"):
            payload = dict(SAMPLE_PAYLOAD)
            payload[field] = "   "
            with self.subTest(field=field):
                with self.assertRaises(UnstructuredIngestionValidationError):
                    ingest_unstructured_fir(payload)

    def test_invalid_metadata_is_rejected(self):
        payload = dict(SAMPLE_PAYLOAD)
        payload["metadata"] = "not-an-object"
        with self.assertRaises(UnstructuredIngestionValidationError):
            ingest_unstructured_fir(payload)


if __name__ == "__main__":
    unittest.main()
