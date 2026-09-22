"""Unit tests for the PostgreSQL investigation repository layer."""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import investigation_repository as repo  # noqa: E402


class InMemoryRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.repository = repo.InMemoryInvestigationRepository()

    def test_insert_list_get_and_update(self):
        record = {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "Trace A",
            "description": "Notes",
            "selected_entity_ids": ["P001"],
            "graph_seeds": ["P001"],
            "from_datetime": None,
            "to_datetime": None,
            "created_by": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }

        self.repository.insert(record)
        self.assertEqual(self.repository.count(), 1)
        self.assertEqual(self.repository.list_all()[0]["name"], "Trace A")

        fetched = self.repository.get_by_id(record["id"])
        self.assertEqual(fetched["selected_entity_ids"], ["P001"])

        updated = self.repository.update_by_id(
            record["id"],
            {"name": "Trace B", "updated_at": "2026-01-02T00:00:00+00:00"},
        )
        self.assertEqual(updated["name"], "Trace B")


class LegacyJsonImportTests(unittest.TestCase):
    def test_imports_json_only_when_store_is_empty(self):
        repository = repo.InMemoryInvestigationRepository()

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "investigations.json"
            json_path.write_text(
                json.dumps(
                    [
                        {
                            "id": "22222222-2222-2222-2222-222222222222",
                            "name": "Legacy trace",
                            "description": None,
                            "selected_entity_ids": ["P010"],
                            "graph_seeds": [],
                            "from_datetime": None,
                            "to_datetime": None,
                            "created_by": None,
                            "created_at": "2026-01-01T00:00:00+00:00",
                            "updated_at": "2026-01-01T00:00:00+00:00",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            imported = repo.import_legacy_json_records(repository, json_path)
            self.assertEqual(imported, 1)
            self.assertEqual(repository.count(), 1)

            imported_again = repo.import_legacy_json_records(repository, json_path)
            self.assertEqual(imported_again, 0)


class PostgresRepositoryTests(unittest.TestCase):
    def test_ensure_schema_executes_create_table(self):
        cursor = MagicMock()
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor

        with patch("app.services.investigation_repository.get_cursor") as mock_cursor:
            mock_cursor.return_value.__enter__.return_value = cursor
            repository = repo.PostgresInvestigationRepository()
            repository.ensure_schema()

        cursor.execute.assert_called()
        executed_sql = " ".join(
            call.args[0] for call in cursor.execute.call_args_list
        )
        self.assertIn("CREATE TABLE IF NOT EXISTS investigations", executed_sql)
        self.assertIn("ADD COLUMN IF NOT EXISTS created_by", executed_sql)
        self.assertIn("ADD COLUMN IF NOT EXISTS jurisdiction", executed_sql)

    def test_insert_fetches_persisted_record(self):
        investigation_id = "33333333-3333-3333-3333-333333333333"
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        row = {
            "id": UUID(investigation_id),
            "name": "Persisted",
            "description": None,
            "selected_entity_ids": ["P003"],
            "graph_seeds": ["P003"],
            "from_datetime": None,
            "to_datetime": None,
            "created_by": None,
            "created_at": now,
            "updated_at": now,
        }

        cursor = MagicMock()
        cursor.fetchone.return_value = row

        with patch("app.services.investigation_repository.get_cursor") as mock_cursor:
            mock_cursor.return_value.__enter__.return_value = cursor
            repository = repo.PostgresInvestigationRepository()
            stored = repository.insert(
                {
                    "id": investigation_id,
                    "name": "Persisted",
                    "description": None,
                    "selected_entity_ids": ["P003"],
                    "graph_seeds": ["P003"],
                    "from_datetime": None,
                    "to_datetime": None,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
            )

        self.assertEqual(stored["id"], investigation_id)
        self.assertEqual(stored["selected_entity_ids"], ["P003"])
        self.assertEqual(cursor.execute.call_count, 2)


if __name__ == "__main__":
    unittest.main()
