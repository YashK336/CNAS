"""Tests for jurisdiction-scoped investigation access control."""

import sys
import unittest
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api import investigations as investigations_api  # noqa: E402
from app.services.auth import hash_password  # noqa: E402
from app.services.investigation_authorization import (  # noqa: E402
    authorize_investigation_read,
    authorize_investigation_update,
    filter_investigations_for_user,
    resolve_create_jurisdiction,
)
from app.services.audit_repository import (  # noqa: E402
    InMemoryAuditRepository,
    set_repository as set_audit_repository,
)
from app.services.investigation_repository import (  # noqa: E402
    InMemoryInvestigationRepository,
    set_repository as set_investigation_repository,
)
from app.services.investigations import InvestigationValidationError  # noqa: E402
from app.services.user_repository import (  # noqa: E402
    InMemoryUserRepository,
    set_repository as set_user_repository,
)
from fastapi import HTTPException  # noqa: E402


def _utc_now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


class JurisdictionTestCase(unittest.TestCase):
    def setUp(self):
        self.users = InMemoryUserRepository()
        self.investigations = InMemoryInvestigationRepository()
        self.audit_logs = InMemoryAuditRepository()
        set_user_repository(self.users)
        set_investigation_repository(self.investigations)
        set_audit_repository(self.audit_logs)

        self.admin = self.users.insert(
            {
                "id": str(uuid.uuid4()),
                "username": "admin",
                "password_hash": hash_password("admin-pass"),
                "role": "ADMIN",
                "jurisdictions": [],
                "created_at": _utc_now_iso(),
            }
        )
        self.analyst_del = self.users.insert(
            {
                "id": str(uuid.uuid4()),
                "username": "analyst-del",
                "password_hash": hash_password("analyst-pass"),
                "role": "ANALYST",
                "jurisdictions": ["DEL"],
                "created_at": _utc_now_iso(),
            }
        )
        self.analyst_multi = self.users.insert(
            {
                "id": str(uuid.uuid4()),
                "username": "analyst-multi",
                "password_hash": hash_password("analyst-pass"),
                "role": "ANALYST",
                "jurisdictions": ["DEL", "MUM"],
                "created_at": _utc_now_iso(),
            }
        )
        self.viewer_mum = self.users.insert(
            {
                "id": str(uuid.uuid4()),
                "username": "viewer-mum",
                "password_hash": hash_password("viewer-pass"),
                "role": "VIEWER",
                "jurisdictions": ["MUM"],
                "created_at": _utc_now_iso(),
            }
        )

    def tearDown(self):
        set_user_repository(None)
        set_investigation_repository(None)
        set_audit_repository(None)

    def _insert_investigation(
        self,
        *,
        name: str,
        jurisdiction: str | None,
        created_by: str | None,
    ) -> dict:
        record = {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": None,
            "selected_entity_ids": [],
            "graph_seeds": [],
            "from_datetime": None,
            "to_datetime": None,
            "created_by": created_by,
            "jurisdiction": jurisdiction,
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        return self.investigations.insert(record)


class SameJurisdictionAccessTests(JurisdictionTestCase):
    def test_analyst_can_read_investigation_in_assigned_jurisdiction(self):
        investigation = self._insert_investigation(
            name="Delhi trace",
            jurisdiction="DEL",
            created_by=self.analyst_del["id"],
        )

        authorize_investigation_read(self.analyst_del, investigation)

        fetched = investigations_api.get_investigation_by_id(
            investigation["id"],
            current_user=self.analyst_del,
        )
        self.assertEqual(fetched["jurisdiction"], "DEL")


class CrossJurisdictionDenialTests(JurisdictionTestCase):
    def test_viewer_cannot_read_investigation_outside_jurisdiction(self):
        investigation = self._insert_investigation(
            name="Delhi trace",
            jurisdiction="DEL",
            created_by=self.analyst_del["id"],
        )

        with self.assertRaises(HTTPException) as ctx:
            investigations_api.get_investigation_by_id(
                investigation["id"],
                current_user=self.viewer_mum,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_analyst_cannot_update_cross_jurisdiction_investigation(self):
        investigation = self._insert_investigation(
            name="Mumbai trace",
            jurisdiction="MUM",
            created_by=self.analyst_multi["id"],
        )

        with self.assertRaises(HTTPException) as ctx:
            investigations_api.put_investigation(
                investigation["id"],
                {"name": "Blocked"},
                current_user=self.analyst_del,
            )
        self.assertEqual(ctx.exception.status_code, 403)


class MultiJurisdictionUserTests(JurisdictionTestCase):
    def test_multi_jurisdiction_analyst_must_select_jurisdiction_on_create(self):
        with self.assertRaises(InvestigationValidationError):
            resolve_create_jurisdiction(self.analyst_multi, {"name": "Needs jurisdiction"})

        jurisdiction = resolve_create_jurisdiction(
            self.analyst_multi,
            {"name": "Needs jurisdiction", "jurisdiction": "MUM"},
        )
        self.assertEqual(jurisdiction, "MUM")

    def test_multi_jurisdiction_analyst_can_access_both_jurisdictions(self):
        delhi = self._insert_investigation(
            name="Delhi trace",
            jurisdiction="DEL",
            created_by=self.analyst_multi["id"],
        )
        mumbai = self._insert_investigation(
            name="Mumbai trace",
            jurisdiction="MUM",
            created_by=self.analyst_multi["id"],
        )

        listing = investigations_api.get_investigations(current_user=self.analyst_multi)
        listed_ids = {item["id"] for item in listing["data"]}
        self.assertEqual(listed_ids, {delhi["id"], mumbai["id"]})


class AdminCrossJurisdictionTests(JurisdictionTestCase):
    def test_admin_can_read_and_update_any_jurisdiction(self):
        investigation = self._insert_investigation(
            name="Delhi trace",
            jurisdiction="DEL",
            created_by=self.analyst_del["id"],
        )

        authorize_investigation_read(self.admin, investigation)
        authorize_investigation_update(self.admin, investigation)

        updated = investigations_api.put_investigation(
            investigation["id"],
            {"name": "Admin override"},
            current_user=self.admin,
        )
        self.assertEqual(updated["name"], "Admin override")

    def test_admin_list_includes_all_jurisdictions(self):
        self._insert_investigation(
            name="Delhi trace",
            jurisdiction="DEL",
            created_by=self.analyst_del["id"],
        )
        self._insert_investigation(
            name="Mumbai trace",
            jurisdiction="MUM",
            created_by=self.analyst_multi["id"],
        )

        listing = investigations_api.get_investigations(current_user=self.admin)
        self.assertEqual(listing["total"], 2)


class LegacyInvestigationAccessTests(JurisdictionTestCase):
    def test_legacy_investigation_is_admin_only(self):
        legacy = self._insert_investigation(
            name="Legacy trace",
            jurisdiction=None,
            created_by=None,
        )

        with self.assertRaises(HTTPException) as ctx:
            authorize_investigation_read(self.viewer_mum, legacy)
        self.assertEqual(ctx.exception.status_code, 403)

        authorize_investigation_read(self.admin, legacy)

        filtered = filter_investigations_for_user(self.analyst_del, [legacy])
        self.assertEqual(filtered, [])


class CreateUpdateAuthorizationTests(JurisdictionTestCase):
    def test_analyst_inherits_single_jurisdiction_on_create(self):
        created = investigations_api.post_investigation(
            {"name": "Inherited jurisdiction"},
            current_user=self.analyst_del,
        )
        self.assertEqual(created["jurisdiction"], "DEL")

    def test_admin_must_provide_jurisdiction_on_create(self):
        with self.assertRaises(HTTPException) as ctx:
            investigations_api.post_investigation(
                {"name": "Missing jurisdiction"},
                current_user=self.admin,
            )
        self.assertEqual(ctx.exception.status_code, 400)

        created = investigations_api.post_investigation(
            {"name": "Admin scoped", "jurisdiction": "MUM"},
            current_user=self.admin,
        )
        self.assertEqual(created["jurisdiction"], "MUM")

    def test_analyst_can_update_own_investigation_in_jurisdiction(self):
        created = investigations_api.post_investigation(
            {"name": "Before"},
            current_user=self.analyst_del,
        )

        updated = investigations_api.put_investigation(
            created["id"],
            {"name": "After"},
            current_user=self.analyst_del,
        )
        self.assertEqual(updated["name"], "After")

    def test_analyst_cannot_create_with_unassigned_jurisdiction(self):
        with self.assertRaises(HTTPException) as ctx:
            investigations_api.post_investigation(
                {"name": "Blocked", "jurisdiction": "MUM"},
                current_user=self.analyst_del,
            )
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
