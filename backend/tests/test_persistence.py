"""Persistence tests: records survive store reinitialization (backend restart)."""

from __future__ import annotations

import json
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import get_cursor  # noqa: E402
from app.services.audit_repository import (  # noqa: E402
    PostgresAuditRepository,
    set_repository as set_audit_repository,
)
from app.services.import_store import (  # noqa: E402
    InMemoryImportRepository,
    PostgresImportRepository,
    create_batch,
    get_batch,
    initialize_import_store,
    list_batches,
    reset_import_store,
    save_batch,
    set_import_repository,
)
from app.services.investigation_repository import (  # noqa: E402
    PostgresInvestigationRepository,
    set_repository as set_investigation_repository,
)


def _utc() -> str:
    return "2026-04-01T00:00:00+00:00"


def _postgres_available() -> bool:
    try:
        with get_cursor() as cursor:
            cursor.execute("SELECT 1 AS ok")
            row = cursor.fetchone()
            return bool(row)
    except Exception:
        return False


class _CursorCtx:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self._cursor

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeInvestigationCursor:
    def __init__(self, table: dict[str, dict]):
        self.table = table
        self._row = None
        self._rows: list[dict] = []

    def execute(self, sql, params=None):
        text = " ".join(sql.split()).lower()
        params = params or {}
        if text.startswith("create") or text.startswith("alter"):
            return
        if text.startswith("insert into investigations"):
            self.table[str(params["id"])] = dict(params)
            return
        if "count(*)" in text:
            self._row = {"total": len(self.table)}
            return
        if "where id" in text and text.startswith("select"):
            self._row = self.table.get(str(params["id"]))
            return
        if text.startswith("update"):
            current = self.table.get(str(params["id"]))
            if current is None:
                self._row = None
                return
            current.update(params)
            self._row = current
            return
        ordered = sorted(
            self.table.values(),
            key=lambda item: str(item.get("updated_at") or ""),
            reverse=True,
        )
        self._rows = ordered
        self._row = ordered[0] if ordered else None

    def fetchone(self):
        return self._row

    def fetchall(self):
        return list(self._rows)


class FakeAuditCursor:
    def __init__(self, records: list[dict]):
        self.records = records
        self._rows: list[dict] = []

    def execute(self, sql, params=None):
        text = " ".join(sql.split()).lower()
        params = params or {}
        if text.startswith("create"):
            return
        if text.startswith("insert into audit_logs"):
            self.records.append(dict(params))
            return
        limit = int(params.get("limit") or 100)
        offset = int(params.get("offset") or 0)
        ordered = list(reversed(self.records))
        self._rows = ordered[offset : offset + limit]

    def fetchall(self):
        return list(self._rows)


class FakeImportCursor:
    def __init__(self, table: dict[str, dict]):
        self.table = table
        self._row = None
        self._rows: list[dict] = []

    def execute(self, sql, params=None):
        text = " ".join(sql.split()).lower()
        params = params or {}
        if text.startswith("create"):
            return
        record = params.get("record")
        if isinstance(record, str):
            record = json.loads(record)
        if text.startswith("insert into import_batches"):
            row = {
                "id": params["id"],
                "created_at": params["created_at"],
                "updated_at": params["updated_at"],
                "status": params["status"],
                "uploader_id": params.get("uploader_id"),
                "record": record,
            }
            self.table[str(params["id"])] = row
            return
        if text.startswith("update"):
            row = {
                "id": params["id"],
                "created_at": params.get("created_at"),
                "updated_at": params["updated_at"],
                "status": params["status"],
                "uploader_id": params.get("uploader_id"),
                "record": record,
            }
            existing = self.table.get(str(params["id"]))
            if existing and not row["created_at"]:
                row["created_at"] = existing.get("created_at")
            self.table[str(params["id"])] = row
            self._row = row
            return
        if "where id" in text:
            self._row = self.table.get(str(params["id"]))
            return
        ordered = sorted(
            self.table.values(),
            key=lambda item: str(item.get("created_at") or ""),
            reverse=True,
        )
        self._rows = ordered

    def fetchone(self):
        return self._row

    def fetchall(self):
        return list(self._rows)


@unittest.skipUnless(_postgres_available(), "PostgreSQL is not reachable")
class LivePostgresPersistenceTests(unittest.TestCase):
    def tearDown(self):
        set_investigation_repository(None)
        set_audit_repository(None)
        reset_import_store()

    def test_investigation_survives_repository_reinitialization(self):
        investigation_id = str(uuid.uuid4())
        first = PostgresInvestigationRepository()
        first.ensure_schema()
        first.insert(
            {
                "id": investigation_id,
                "name": "Persist me",
                "description": "restart check",
                "selected_entity_ids": ["P001"],
                "graph_seeds": ["P001"],
                "from_datetime": None,
                "to_datetime": None,
                "created_by": None,
                "jurisdiction": "DEL",
                "created_at": _utc(),
                "updated_at": _utc(),
            }
        )
        set_investigation_repository(None)
        second = PostgresInvestigationRepository()
        fetched = second.get_by_id(investigation_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["name"], "Persist me")
        self.assertEqual(fetched["jurisdiction"], "DEL")
        self.assertEqual(fetched["selected_entity_ids"], ["P001"])
        with get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM investigations WHERE id = %(id)s",
                {"id": investigation_id},
            )

    def test_audit_log_survives_repository_reinitialization(self):
        event_id = str(uuid.uuid4())
        first = PostgresAuditRepository()
        first.ensure_schema()
        first.append(
            {
                "id": event_id,
                "timestamp": _utc(),
                "user_id": None,
                "action": "investigation.create",
                "resource_type": "investigation",
                "resource_id": "inv-1",
                "jurisdiction": "DEL",
                "result": "success",
                "metadata": {"name": "Persist me"},
            }
        )
        set_audit_repository(None)
        second = PostgresAuditRepository()
        events = second.list_events(limit=500, offset=0)
        match = [event for event in events if event["id"] == event_id]
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]["action"], "investigation.create")
        self.assertEqual(match[0]["jurisdiction"], "DEL")
        self.assertEqual(match[0]["metadata"]["name"], "Persist me")
        with get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM audit_logs WHERE id = %(id)s",
                {"id": event_id},
            )

    def test_import_history_survives_store_reinitialization(self):
        set_import_repository(PostgresImportRepository())
        initialize_import_store()
        created = create_batch(
            {
                "filename": "persist.csv",
                "status": "complete",
                "uploader_id": "user-1",
                "uploader_username": "analyst-del",
                "row_count": 2,
                "rows": [{"fir_id": "FIR-PERSIST"}],
            }
        )
        import_id = created["id"]
        save_batch(import_id, {"status": "complete", "result": {"imported": 2}})
        set_import_repository(None)
        initialize_import_store()
        fetched = get_batch(import_id)
        self.assertEqual(fetched["filename"], "persist.csv")
        self.assertEqual(fetched["uploader_id"], "user-1")
        self.assertEqual(fetched["result"]["imported"], 2)
        self.assertEqual(fetched["rows"][0]["fir_id"], "FIR-PERSIST")
        listed = list_batches()
        self.assertTrue(any(item["id"] == import_id for item in listed))
        with get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM import_batches WHERE id = %(id)s",
                {"id": import_id},
            )


class FakePostgresPersistenceTests(unittest.TestCase):
    def test_investigation_survives_new_repository_instance(self):
        table: dict[str, dict] = {}
        investigation_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

        def fake_cursor():
            return _CursorCtx(FakeInvestigationCursor(table))

        with patch(
            "app.services.investigation_repository.get_cursor",
            side_effect=fake_cursor,
        ):
            first = PostgresInvestigationRepository()
            first.ensure_schema()
            first.insert(
                {
                    "id": investigation_id,
                    "name": "Fake persist",
                    "description": None,
                    "selected_entity_ids": ["P010"],
                    "graph_seeds": [],
                    "from_datetime": None,
                    "to_datetime": None,
                    "created_by": None,
                    "jurisdiction": "MUM",
                    "created_at": _utc(),
                    "updated_at": _utc(),
                }
            )
            second = PostgresInvestigationRepository()
            fetched = second.get_by_id(investigation_id)
        self.assertEqual(fetched["name"], "Fake persist")
        self.assertEqual(fetched["jurisdiction"], "MUM")

    def test_audit_survives_new_repository_instance(self):
        records: list[dict] = []
        event_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

        def fake_cursor():
            return _CursorCtx(FakeAuditCursor(records))

        with patch("app.services.audit_repository.get_cursor", side_effect=fake_cursor):
            first = PostgresAuditRepository()
            first.ensure_schema()
            first.append(
                {
                    "id": event_id,
                    "timestamp": _utc(),
                    "user_id": None,
                    "action": "auth.login.success",
                    "resource_type": "user",
                    "resource_id": "u1",
                    "jurisdiction": None,
                    "result": "success",
                    "metadata": {"username": "admin"},
                }
            )
            second = PostgresAuditRepository()
            events = second.list_events(limit=10, offset=0)
        self.assertEqual(events[0]["id"], event_id)
        self.assertEqual(events[0]["action"], "auth.login.success")

    def test_import_survives_new_repository_instance(self):
        table: dict[str, dict] = {}

        def fake_cursor():
            return _CursorCtx(FakeImportCursor(table))

        with patch("app.services.import_store.get_cursor", side_effect=fake_cursor):
            first = PostgresImportRepository()
            first.ensure_schema()
            created = first.insert(
                {
                    "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                    "created_at": _utc(),
                    "updated_at": _utc(),
                    "filename": "cases.csv",
                    "status": "draft",
                    "uploader_id": "analyst-1",
                    "rows": [{"fir_id": "FIR1"}],
                }
            )
            first.update(created["id"], {"status": "complete"})
            second = PostgresImportRepository()
            fetched = second.get(created["id"])
            listed = second.list_all()
        self.assertEqual(fetched["status"], "complete")
        self.assertEqual(fetched["filename"], "cases.csv")
        self.assertEqual(listed[0]["id"], created["id"])


class MemoryStoreStillAvailableTests(unittest.TestCase):
    def tearDown(self):
        reset_import_store()

    def test_in_memory_import_store_does_not_survive_reset(self):
        reset_import_store()
        created = create_batch({"filename": "temp.csv", "status": "draft"})
        self.assertEqual(get_batch(created["id"])["filename"], "temp.csv")
        reset_import_store()
        with self.assertRaises(Exception):
            get_batch(created["id"])

    def test_in_memory_repository_can_be_injected(self):
        repo = InMemoryImportRepository()
        set_import_repository(repo)
        created = create_batch({"filename": "injected.csv", "status": "draft"})
        self.assertEqual(repo.get(created["id"])["filename"], "injected.csv")
