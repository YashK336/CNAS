"""Tests for saved investigation JSON persistence and API handlers."""

import sys
import unittest
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api import investigations as investigations_api  # noqa: E402
from app.services import investigations as investigations_service  # noqa: E402
from app.services.audit_repository import (  # noqa: E402
    InMemoryAuditRepository,
    set_repository as set_audit_repository,
)
from app.services.investigation_repository import (  # noqa: E402
    InMemoryInvestigationRepository,
    set_repository,
)
from fastapi import HTTPException  # noqa: E402


def _analyst_user() -> dict:
    return {
        "id": str(uuid.uuid4()),
        "username": "analyst",
        "role": "ANALYST",
        "jurisdictions": ["MH"],
        "password_hash": "hashed",
        "created_at": "2026-01-01T00:00:00+00:00",
    }


class InvestigationServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryInvestigationRepository()
        self.audit_logs = InMemoryAuditRepository()
        set_repository(self.repository)
        set_audit_repository(self.audit_logs)
        self.analyst = _analyst_user()

    def tearDown(self):
        set_repository(None)
        set_audit_repository(None)

    def test_create_list_and_get_investigation(self):
        created = investigations_service.create_investigation(
            {
                "name": "Drug network trace",
                "description": "P001 to P003 with January window",
                "selected_entity_ids": ["P001", "P003"],
                "graph_seeds": ["P001"],
                "from_datetime": "2026-01-01T00:00:00",
                "to_datetime": "2026-01-31T23:59:59",
            },
            created_by=self.analyst["id"],
            jurisdiction="MH",
        )

        self.assertTrue(created["id"])
        self.assertEqual(created["name"], "Drug network trace")
        self.assertEqual(created["selected_entity_ids"], ["P001", "P003"])
        self.assertEqual(created["created_by"], self.analyst["id"])

        listing = investigations_service.list_investigations()
        self.assertEqual(listing["total"], 1)
        self.assertEqual(listing["data"][0]["id"], created["id"])

        fetched = investigations_service.get_investigation(created["id"])
        self.assertEqual(fetched["graph_seeds"], ["P001"])

    def test_update_investigation(self):
        created = investigations_service.create_investigation(
            {"name": "Initial name", "description": "Draft"},
            created_by=self.analyst["id"],
            jurisdiction="MH",
        )

        updated = investigations_service.update_investigation(
            created["id"],
            {
                "name": "Updated name",
                "selected_entity_ids": ["P002"],
                "graph_seeds": ["P002"],
            },
        )

        self.assertEqual(updated["name"], "Updated name")
        self.assertEqual(updated["selected_entity_ids"], ["P002"])
        self.assertEqual(updated["description"], "Draft")
        self.assertGreaterEqual(updated["updated_at"], created["updated_at"])

    def test_get_missing_investigation_raises(self):
        with self.assertRaises(investigations_service.InvestigationNotFoundError):
            investigations_service.get_investigation("missing-id")

    def test_create_requires_name(self):
        with self.assertRaises(investigations_service.InvestigationValidationError):
            investigations_service.create_investigation({"description": "No name"})

    def test_create_rejects_invalid_selected_entity_ids(self):
        with self.assertRaises(investigations_service.InvestigationValidationError):
            investigations_service.create_investigation(
                {"name": "Bad ids", "selected_entity_ids": ["P001", 42]}
            )

    def test_update_rejects_empty_payload(self):
        created = investigations_service.create_investigation({"name": "Example"}, jurisdiction="MH")
        with self.assertRaises(investigations_service.InvestigationValidationError):
            investigations_service.update_investigation(created["id"], {})


class InvestigationEndpointTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryInvestigationRepository()
        self.audit_logs = InMemoryAuditRepository()
        set_repository(self.repository)
        set_audit_repository(self.audit_logs)
        self.analyst = _analyst_user()

    def tearDown(self):
        set_repository(None)
        set_audit_repository(None)

    def test_post_and_get_endpoints(self):
        created = investigations_api.post_investigation(
            {
                "name": "Endpoint create",
                "selected_entity_ids": ["P004"],
            },
            current_user=self.analyst,
        )
        self.assertEqual(created["name"], "Endpoint create")

        fetched = investigations_api.get_investigation_by_id(
            created["id"],
            current_user=self.analyst,
        )
        self.assertEqual(fetched["selected_entity_ids"], ["P004"])

        listing = investigations_api.get_investigations(current_user=self.analyst)
        self.assertEqual(listing["total"], 1)

    def test_put_endpoint_updates_record(self):
        created = investigations_api.post_investigation(
            {"name": "Before"},
            current_user=self.analyst,
        )
        updated = investigations_api.put_investigation(
            created["id"],
            {"name": "After", "graph_seeds": ["P005"]},
            current_user=self.analyst,
        )
        self.assertEqual(updated["name"], "After")
        self.assertEqual(updated["graph_seeds"], ["P005"])

    def test_get_missing_returns_404(self):
        with self.assertRaises(HTTPException) as ctx:
            investigations_api.get_investigation_by_id(
                "missing",
                current_user=self.analyst,
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_post_invalid_payload_returns_400(self):
        with self.assertRaises(HTTPException) as ctx:
            investigations_api.post_investigation(
                {"name": "   "},
                current_user=self.analyst,
            )
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
