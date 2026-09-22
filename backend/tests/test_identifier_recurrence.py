"""AN-2 cross-jurisdictional identifier recurrence tests."""

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.an2_input import parse_an2_input  # noqa: E402
from app.services.identifier_recurrence import detect_identifier_recurrence  # noqa: E402
from app.services.unstructured_ingestion import ingest_unstructured_fir  # noqa: E402
from app.api.analytics import get_an2_identifier_recurrence  # noqa: E402


def _record(case_ref: str, jurisdiction: str, text: str, event_date: str) -> dict:
    return ingest_unstructured_fir(
        {
            "source": "unstructured_fir",
            "source_ref": case_ref,
            "jurisdiction": jurisdiction,
            "text": text,
            "metadata": {"event_date": event_date},
        },
        ingested_at="2026-01-01T00:00:00+00:00",
    )


class IdentifierRecurrenceTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            _record("FIR-DEL-1", "DEL", "Phone +91-90000-10001 observed.", "2026-01-02"),
            _record("FIR-MUM-2", "MUM", "Phone +91-90000-10001 observed.", "2026-02-03"),
            _record("FIR-BLR-3", "BLR", "Phone +91-90000-10001 observed.", "2026-03-04"),
        ]

    def test_requires_three_cases_and_two_jurisdictions(self):
        findings = detect_identifier_recurrence(self.records)

        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding["finding_type"], "AN-2")
        self.assertEqual(finding["cases"], ["FIR-BLR-3", "FIR-DEL-1", "FIR-MUM-2"])
        self.assertEqual(finding["jurisdictions"], ["BLR", "DEL", "MUM"])
        self.assertEqual(finding["valid_from"], "2026-01-02")
        self.assertEqual(finding["valid_to"], "2026-03-04")
        self.assertTrue(all(item["valid_to"] is None for item in finding["evidence"]))

    def test_finding_range_uses_earliest_and_latest_event_dates(self):
        records = [
            _record("FIR-DEL-1", "DEL", "Phone +91-90000-10001 observed.", "2026-01-02"),
            _record("FIR-MUM-2", "MUM", "Phone +91-90000-10001 observed.", "2026-02-15"),
            _record("FIR-BLR-3", "BLR", "Phone +91-90000-10001 observed.", "2026-03-21"),
        ]

        finding = detect_identifier_recurrence(records)[0]

        self.assertEqual(finding["valid_from"], "2026-01-02")
        self.assertEqual(finding["valid_to"], "2026-03-21")

    def test_duplicate_document_and_duplicate_mentions_do_not_inflate_cases(self):
        duplicate = _record("FIR-DEL-1", "DEL", "Phone +91-90000-10001 and +91-90000-10001.", "2026-01-02")
        findings = detect_identifier_recurrence([duplicate, duplicate, *self.records[1:]])

        self.assertEqual(len(findings), 1)
        self.assertEqual(len(findings[0]["cases"]), 3)
        self.assertEqual(len(findings[0]["evidence"]), 3)

    def test_findings_include_complete_claim_evidence_method_confidence_and_limits(self):
        finding = detect_identifier_recurrence(self.records)[0]

        self.assertTrue(finding["claim"])
        self.assertEqual(len(finding["evidence"]), 3)
        self.assertEqual(finding["method"]["name"], "identifier_recurrence_v1")
        self.assertGreaterEqual(finding["confidence"], 0.0)
        self.assertTrue(finding["limits"])
        for evidence in finding["evidence"]:
            self.assertTrue(evidence["source_ref"])
            self.assertTrue(evidence["content_hash"])
            self.assertTrue(evidence["ingested_at"])
            self.assertTrue(evidence["jurisdiction"])
            self.assertIn("valid_from", evidence)

    def test_below_threshold_is_not_a_finding(self):
        findings = detect_identifier_recurrence(self.records[:2])

        self.assertEqual(findings, [])

    def test_analytics_endpoint_returns_an2_envelope(self):
        payload = [
            {
                "source": "unstructured_fir",
                "source_ref": record["data"]["source_ref"],
                "jurisdiction": record["data"]["jurisdiction"],
                "text": record["data"]["text"],
                "metadata": record["data"]["metadata"],
            }
            for record in self.records
        ]

        response = get_an2_identifier_recurrence(payload)

        self.assertEqual(response["finding_type"], "AN-2")
        self.assertEqual(response["total"], 1)


UP21_FIR_001 = (
    "On 12/01/2026, the complainant reported that an unknown individual arrived "
    "near the market area in a white SUV bearing registration UP21AB4587. The "
    "person was seen leaving the location shortly after the incident. A mobile "
    "number 9876543210 was mentioned by a witness during the preliminary inquiry. "
    "CCTV footage from the nearby shops has been collected for further investigation."
)
UP21_FIR_014 = (
    "During investigation of a theft reported on 18/02/2026, officers reviewed "
    "CCTV footage showing a white SUV with registration number UP21AB4587 near "
    "the reported location. The vehicle was observed approximately 20 minutes "
    "before the incident and subsequently left the area. The investigating officer "
    "has requested additional information regarding the vehicle and its registered owner."
)
UP21_FIR_029 = (
    "On 21/03/2026, a witness reported seeing a white SUV bearing registration "
    "UP21AB4587 near the location of a suspected financial fraud. The vehicle was "
    "parked outside the premises for several minutes before leaving. A separate "
    "witness provided mobile number 9876543210 during questioning. CCTV footage "
    "and witness statements have been preserved as evidence."
)

UP21_CSV = (
    "fir_id,raw_text\n"
    f'FIR-2026-001,"{UP21_FIR_001}"\n'
    f'FIR-2026-014,"{UP21_FIR_014}"\n'
    f'FIR-2026-029,"{UP21_FIR_029}"\n'
)

UP21_CSV_WITH_JURISDICTION = (
    "fir_id,raw_text,jurisdiction\n"
    f'FIR-2026-001,"{UP21_FIR_001}",DEL\n'
    f'FIR-2026-014,"{UP21_FIR_014}",MUM\n'
    f'FIR-2026-029,"{UP21_FIR_029}",BLR\n'
)

UP21_JSON = [
    {
        "source": "unstructured_fir",
        "source_ref": "FIR-2026-001",
        "jurisdiction": "DEL",
        "text": UP21_FIR_001,
    },
    {
        "source": "unstructured_fir",
        "source_ref": "FIR-2026-014",
        "jurisdiction": "MUM",
        "text": UP21_FIR_014,
    },
    {
        "source": "unstructured_fir",
        "source_ref": "FIR-2026-029",
        "jurisdiction": "BLR",
        "text": UP21_FIR_029,
    },
]


class An2InputParsingTests(unittest.TestCase):
    def test_json_aliases_normalize_to_canonical_schema(self):
        items = parse_an2_input(
            [
                {
                    "fir_id": "FIR-2026-001",
                    "raw_text": UP21_FIR_001,
                    "jurisdiction": "DEL",
                }
            ]
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source"], "unstructured_fir")
        self.assertEqual(items[0]["source_ref"], "FIR-2026-001")
        self.assertEqual(items[0]["jurisdiction"], "DEL")
        self.assertEqual(items[0]["text"], UP21_FIR_001)

    def test_csv_fir_id_raw_text_normalizes_to_canonical_schema(self):
        items = parse_an2_input(UP21_CSV)

        self.assertEqual([item["source_ref"] for item in items], [
            "FIR-2026-001",
            "FIR-2026-014",
            "FIR-2026-029",
        ])
        for item in items:
            self.assertEqual(item["source"], "unstructured_fir")
            self.assertEqual(item["jurisdiction"], "UNSPECIFIED")
            self.assertIn("UP21AB4587", item["text"])
            ingest_unstructured_fir(item)

    def test_existing_json_records_remain_canonical(self):
        items = parse_an2_input(UP21_JSON)

        self.assertEqual(items[0]["source"], "unstructured_fir")
        self.assertEqual(items[0]["source_ref"], "FIR-2026-001")
        self.assertEqual(items[0]["jurisdiction"], "DEL")
        self.assertEqual(items[0]["text"], UP21_FIR_001)

    def test_up21ab4587_recurrence_from_json(self):
        response = get_an2_identifier_recurrence(UP21_JSON)

        self.assertEqual(response["finding_type"], "AN-2")
        vehicle = next(
            finding
            for finding in response["data"]
            if finding["identifier"]["value"] == "UP21AB4587"
        )
        self.assertEqual(vehicle["cases"], ["FIR-2026-001", "FIR-2026-014", "FIR-2026-029"])
        self.assertEqual(vehicle["jurisdictions"], ["BLR", "DEL", "MUM"])
        phones = [
            finding
            for finding in response["data"]
            if finding["identifier"]["type"] == "phone"
        ]
        self.assertEqual(phones, [])

    def test_up21ab4587_recurrence_from_csv(self):
        response = get_an2_identifier_recurrence(UP21_CSV_WITH_JURISDICTION)

        self.assertEqual(response["total"], 1)
        finding = response["data"][0]
        self.assertEqual(finding["identifier"]["type"], "vehicle")
        self.assertEqual(finding["identifier"]["value"], "UP21AB4587")
        self.assertEqual(finding["cases"], ["FIR-2026-001", "FIR-2026-014", "FIR-2026-029"])
        self.assertEqual(finding["jurisdictions"], ["BLR", "DEL", "MUM"])

    def test_csv_without_second_jurisdiction_keeps_an2_thresholds(self):
        response = get_an2_identifier_recurrence(UP21_CSV)

        self.assertEqual(response["finding_type"], "AN-2")
        self.assertEqual(response["total"], 0)
        self.assertEqual(response["data"], [])


if __name__ == "__main__":
    unittest.main()
