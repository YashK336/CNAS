"""Ingestion and normalization tests."""

import sys
import unittest
from pathlib import Path

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.ingestion import (  # noqa: E402
    SOURCE_FILES,
    load_cdr,
    load_entity_mapping,
    load_finance,
    load_fir,
    load_persons,
    load_records_with_duplicates,
    load_social,
    load_source_records,
    load_surveillance,
    load_vehicles,
)
from app.services.normalization import (  # noqa: E402
    find_duplicate_hashes,
    hash_record_content,
    normalize_dataframe,
    normalize_row,
)


class NormalizationTests(unittest.TestCase):
    def test_normalized_record_structure(self):
        row = pd.Series(
            {
                "person_id": "P001",
                "name": "Rajesh Kumar",
                "phone": "+91-90000-10001",
                "home_city": "Mumbai",
            }
        )

        record = normalize_row("persons", row, 0, ingested_at="2026-01-01T00:00:00+00:00")

        self.assertEqual(record["source"], "persons")
        self.assertEqual(record["record_id"], "persons:P001")
        self.assertEqual(record["ingested_at"], "2026-01-01T00:00:00+00:00")
        self.assertEqual(len(record["content_hash"]), 64)
        self.assertEqual(record["data"]["person_id"], "P001")
        self.assertEqual(record["data"]["name"], "Rajesh Kumar")

    def test_hash_is_deterministic(self):
        data = {
            "person_id": "P001",
            "name": "Rajesh Kumar",
            "phone": "+91-90000-10001",
        }

        first = hash_record_content("persons", data)
        second = hash_record_content("persons", data)

        self.assertEqual(first, second)

    def test_hash_changes_when_data_changes(self):
        base = {"person_id": "P001", "name": "Rajesh Kumar"}
        changed = {"person_id": "P001", "name": "Amit Kumar"}

        self.assertNotEqual(
            hash_record_content("persons", base),
            hash_record_content("persons", changed),
        )

    def test_duplicate_detection(self):
        row = pd.Series({"person_id": "P001", "name": "Duplicate"})
        records = [
            normalize_row("persons", row, 0, ingested_at="2026-01-01T00:00:00+00:00"),
            normalize_row("persons", row, 1, ingested_at="2026-01-01T00:00:00+00:00"),
        ]

        duplicates = find_duplicate_hashes(records)

        self.assertEqual(len(duplicates), 1)
        only_group = next(iter(duplicates.values()))
        self.assertEqual(len(only_group), 2)

    def test_duplicate_detection_does_not_drop_records(self):
        df = pd.DataFrame(
            [
                {
                    "person_id": "PX1",
                    "name": "Same",
                    "phone": "+91-90000-19999",
                    "home_city": "Mumbai",
                },
                {
                    "person_id": "PX1",
                    "name": "Same",
                    "phone": "+91-90000-19999",
                    "home_city": "Mumbai",
                },
            ]
        )
        records = normalize_dataframe("persons", df, ingested_at="2026-01-01T00:00:00+00:00")

        self.assertEqual(len(records), 2)
        self.assertEqual(len(find_duplicate_hashes(records)), 1)


class LoaderTests(unittest.TestCase):
    def setUp(self):
        from app.services.import_overlay import configure_overlay, reset_overlay

        configure_overlay(persist=False)
        reset_overlay()

    def tearDown(self):
        from app.services.import_overlay import configure_overlay, reset_overlay

        reset_overlay()
        configure_overlay(persist=False)

    def test_existing_persons_loader(self):
        df = load_persons()

        self.assertEqual(len(df), 50)
        self.assertIn("person_id", df.columns)
        self.assertIn("name", df.columns)

    def test_all_source_loaders_return_dataframes(self):
        loaders = [
            load_persons,
            load_vehicles,
            load_cdr,
            load_finance,
            load_fir,
            load_social,
            load_surveillance,
            load_entity_mapping,
        ]

        for loader in loaders:
            df = loader()
            self.assertGreater(len(df), 0)
            self.assertGreater(len(df.columns), 0)

    def test_load_source_records_for_every_source(self):
        for source in SOURCE_FILES:
            records = load_source_records(source)
            self.assertGreater(len(records), 0)
            self.assertEqual(records[0]["source"], source)
            self.assertIn("content_hash", records[0])

    def test_real_dataset_duplicate_detection_preserves_records(self):
        for source in SOURCE_FILES:
            records, duplicates = load_records_with_duplicates(source)
            self.assertEqual(len(records), len(load_source_records(source)))

            for record_ids in duplicates.values():
                self.assertGreaterEqual(len(record_ids), 2)

    def test_overlay_rows_are_json_serializable_on_reload(self):
        import json

        from app.api.entities import get_persons
        from app.services.import_overlay import append_overlay_rows, reset_overlay

        reset_overlay()
        append_overlay_rows(
            "persons",
            [
                {
                    "person_id": "IMP-OVERLAY-1",
                    "name": "Overlay Person",
                    "phone": None,
                    "vehicle_no": None,
                    "_import_id": "batch-1",
                    "_ingested_at": "2026-09-17T00:00:00+00:00",
                }
            ],
        )
        first = get_persons()
        encoded = json.dumps(first)
        self.assertIn("Overlay Person", encoded)
        self.assertNotIn("NaN", encoded)
        reload_payload = get_persons()
        json.dumps(reload_payload)
        self.assertIn(
            "Overlay Person",
            {row.get("name") for row in reload_payload["data"]},
        )
        reset_overlay()


if __name__ == "__main__":
    unittest.main()
