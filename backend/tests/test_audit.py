"""Tests for append-only audit logging."""

import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api import auth as auth_api  # noqa: E402
from app.api import audit_logs as audit_logs_api  # noqa: E402
from app.api import adjudication as adjudication_api  # noqa: E402
from app.api import imports as imports_api  # noqa: E402
from app.api import investigations as investigations_api  # noqa: E402
from app.core import security  # noqa: E402
from app.services.audit_repository import (  # noqa: E402
    InMemoryAuditRepository,
    set_repository as set_audit_repository,
)
from app.services.audit_service import (  # noqa: E402
    AuditWriteError,
    audit_auth_login_failure,
    audit_auth_login_success,
    audit_auth_unauthenticated,
    record_audit_event,
    sanitize_metadata,
)
from app.services.auth import hash_password  # noqa: E402
from app.services.import_overlay import (  # noqa: E402
    DEFAULT_OVERLAY_DIR,
    configure_overlay,
    reset_overlay,
)
from app.services.import_store import reset_import_store  # noqa: E402
from app.services.investigation_repository import (  # noqa: E402
    InMemoryInvestigationRepository,
    set_repository as set_investigation_repository,
)
from app.services.review_repository import (  # noqa: E402
    InMemoryReviewRepository,
    set_repository as set_review_repository,
)
from app.services.user_repository import (  # noqa: E402
    InMemoryUserRepository,
    set_repository as set_user_repository,
)
from fastapi import HTTPException  # noqa: E402


JWT_SETTINGS = {
    "secret": "test-secret-key",
    "algorithm": "HS256",
    "expire_minutes": 30,
}


def _utc_now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


class FailingAuditRepository:
    def ensure_schema(self) -> None:
        return None

    def append(self, record):
        raise RuntimeError("audit store unavailable")


class AuditTestCase(unittest.TestCase):
    def setUp(self):
        self.users = InMemoryUserRepository()
        self.investigations = InMemoryInvestigationRepository()
        self.reviews = InMemoryReviewRepository()
        self.audit_logs = InMemoryAuditRepository()
        set_user_repository(self.users)
        set_investigation_repository(self.investigations)
        set_review_repository(self.reviews)
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
        self.analyst = self.users.insert(
            {
                "id": str(uuid.uuid4()),
                "username": "analyst",
                "password_hash": hash_password("analyst-pass"),
                "role": "ANALYST",
                "jurisdictions": ["DEL"],
                "created_at": _utc_now_iso(),
            }
        )
        self.viewer = self.users.insert(
            {
                "id": str(uuid.uuid4()),
                "username": "viewer",
                "password_hash": hash_password("viewer-pass"),
                "role": "VIEWER",
                "jurisdictions": ["DEL"],
                "created_at": _utc_now_iso(),
            }
        )

        self.settings_patch = patch(
            "app.core.security.jwt_settings",
            return_value=JWT_SETTINGS,
        )
        self.settings_patch.start()
        configure_overlay(directory=DEFAULT_OVERLAY_DIR, persist=False)
        reset_overlay()
        reset_import_store()

    def tearDown(self):
        self.settings_patch.stop()
        reset_overlay()
        configure_overlay(directory=DEFAULT_OVERLAY_DIR, persist=False)
        reset_import_store()
        set_user_repository(None)
        set_investigation_repository(None)
        set_review_repository(None)
        set_audit_repository(None)


class SuccessfulActionAuditTests(AuditTestCase):
    def test_login_success_is_audited(self):
        auth_api.post_login({"username": "analyst", "password": "analyst-pass"})
        events = self.audit_logs.list_all()
        self.assertEqual(events[-1]["action"], "auth.login.success")
        self.assertEqual(events[-1]["result"], "success")
        self.assertEqual(events[-1]["user_id"], self.analyst["id"])

    def test_investigation_create_and_update_are_audited(self):
        created = investigations_api.post_investigation(
            {"name": "Audited trace"},
            current_user=self.analyst,
        )
        investigations_api.put_investigation(
            created["id"],
            {"name": "Updated trace"},
            current_user=self.analyst,
        )

        actions = [event["action"] for event in self.audit_logs.list_all()]
        self.assertIn("investigation.create", actions)
        self.assertIn("investigation.update", actions)
        self.assertNotIn("investigation.list", actions)


class NavigationAuditPolicyTests(AuditTestCase):
    def _create_pending_review(self) -> dict:
        from app.services.adjudication_service import create_review_from_resolution
        from app.services.resolution_config import METHOD_EXACT_PHONE, RESOLUTION_STATUS_AMBIGUOUS

        review = create_review_from_resolution(
            result={
                "candidate_value": "+919000010099",
                "entity_type": "phone",
                "matched_entity_id": None,
                "confidence": 1.0,
                "method": METHOD_EXACT_PHONE,
                "status": RESOLUTION_STATUS_AMBIGUOUS,
                "proposed_entity_ids": ["P100", "P101"],
            },
            jurisdiction="DEL",
        )
        assert review is not None
        return review

    def test_investigation_list_and_read_do_not_create_audit_events(self):
        created = investigations_api.post_investigation(
            {"name": "Navigation noise check"},
            current_user=self.analyst,
        )
        baseline = len(self.audit_logs.list_all())

        investigations_api.get_investigations(current_user=self.analyst)
        investigations_api.get_investigations(current_user=self.analyst)
        investigations_api.get_investigation_by_id(
            created["id"],
            current_user=self.analyst,
        )

        self.assertEqual(len(self.audit_logs.list_all()), baseline)

    def test_audit_log_page_load_does_not_create_audit_events(self):
        baseline = len(self.audit_logs.list_all())

        audit_logs_api.get_audit_logs(
            limit=100,
            offset=0,
            current_user=self.admin,
        )
        audit_logs_api.get_audit_logs(
            limit=100,
            offset=0,
            current_user=self.admin,
        )

        actions = [event["action"] for event in self.audit_logs.list_all()[baseline:]]
        self.assertEqual(actions, [])

    def test_adjudication_queue_navigation_does_not_create_audit_events(self):
        self._create_pending_review()
        baseline = len(self.audit_logs.list_all())

        adjudication_api.get_pending_reviews(current_user=self.analyst)
        review = adjudication_api.get_pending_reviews(current_user=self.analyst)["reviews"][0]
        adjudication_api.get_review_by_id(
            review["review_id"],
            current_user=self.analyst,
        )
        adjudication_api.get_pending_reviews(current_user=self.analyst)

        actions = [event["action"] for event in self.audit_logs.list_all()[baseline:]]
        self.assertEqual(actions, [])

    def test_adjudication_confirm_remains_audited(self):
        review = self._create_pending_review()
        adjudication_api.post_confirm_review(
            review["review_id"],
            {"canonical_entity_id": "P100"},
            current_user=self.analyst,
        )
        actions = [event["action"] for event in self.audit_logs.list_all()]
        self.assertIn("adjudication.review.confirm", actions)

    def _manual_import_payload(self) -> dict:
        return {
            "fir_id": "FIR-AUD-NAV-1",
            "date": "2026-03-14",
            "crime": "fraud",
            "name": "Audit Navigation Person",
            "phone": "9876500011",
        }

    def test_import_history_and_detail_reads_do_not_create_audit_events(self):
        created = imports_api.post_inspect_manual(
            self._manual_import_payload(),
            current_user=self.analyst,
        )
        inspect_actions = [
            event["action"] for event in self.audit_logs.list_all()
        ]
        self.assertIn("data_import.inspect", inspect_actions)
        baseline = len(self.audit_logs.list_all())

        imports_api.get_imports(current_user=self.analyst)
        imports_api.get_imports(current_user=self.analyst)
        imports_api.get_import(created["id"], current_user=self.analyst)

        actions = [event["action"] for event in self.audit_logs.list_all()[baseline:]]
        self.assertEqual(actions, [])
        self.assertNotIn(
            "data_import.read",
            [event["action"] for event in self.audit_logs.list_all()],
        )

    def test_import_inspect_and_confirm_remain_audited(self):
        created = imports_api.post_inspect_manual(
            self._manual_import_payload(),
            current_user=self.analyst,
        )
        imports_api.post_confirm(
            created["id"],
            {"continue_with_warnings": True},
            current_user=self.analyst,
        )
        actions = [event["action"] for event in self.audit_logs.list_all()]
        self.assertIn("data_import.inspect", actions)
        self.assertIn("data_import.confirm", actions)
        self.assertNotIn("data_import.read", actions)

    def test_import_denied_access_remains_audited(self):
        created = imports_api.post_inspect_manual(
            self._manual_import_payload(),
            current_user=self.analyst,
        )
        baseline = len(self.audit_logs.list_all())

        with self.assertRaises(HTTPException) as write_ctx:
            imports_api.post_inspect_manual(
                self._manual_import_payload(),
                current_user=self.viewer,
            )
        self.assertEqual(write_ctx.exception.status_code, 403)

        with self.assertRaises(HTTPException) as read_ctx:
            imports_api.get_import(created["id"], current_user=self.viewer)
        self.assertEqual(read_ctx.exception.status_code, 403)

        actions = [
            (event["action"], event["result"])
            for event in self.audit_logs.list_all()[baseline:]
        ]
        self.assertIn(("authorization.role.denied", "denied"), actions)
        self.assertIn(("data_import.read", "denied"), actions)
        self.assertNotIn(("data_import.read", "success"), actions)


class DeniedActionAuditTests(AuditTestCase):
    def test_login_failure_is_audited(self):
        with self.assertRaises(HTTPException) as ctx:
            auth_api.post_login({"username": "analyst", "password": "wrong"})
        self.assertEqual(ctx.exception.status_code, 401)

        event = self.audit_logs.list_all()[-1]
        self.assertEqual(event["action"], "auth.login.failure")
        self.assertEqual(event["result"], "failure")
        self.assertIsNone(event["user_id"])
        self.assertEqual(event["metadata"]["username"], "analyst")

    def test_role_denial_is_audited(self):
        with self.assertRaises(HTTPException) as ctx:
            investigations_api.post_investigation(
                {"name": "Blocked"},
                current_user=self.viewer,
            )
        self.assertEqual(ctx.exception.status_code, 403)

        event = self.audit_logs.list_all()[-1]
        self.assertEqual(event["action"], "authorization.role.denied")
        self.assertEqual(event["result"], "denied")

    def test_cross_jurisdiction_read_denial_is_audited(self):
        created = investigations_api.post_investigation(
            {"name": "Mumbai trace", "jurisdiction": "MUM"},
            current_user=self.admin,
        )

        with self.assertRaises(HTTPException) as ctx:
            investigations_api.get_investigation_by_id(
                created["id"],
                current_user=self.viewer,
            )
        self.assertEqual(ctx.exception.status_code, 403)

        event = self.audit_logs.list_all()[-1]
        self.assertEqual(event["action"], "investigation.read")
        self.assertEqual(event["result"], "denied")


class UnauthenticatedEventAuditTests(AuditTestCase):
    def test_missing_token_is_audited(self):
        with self.assertRaises(HTTPException) as ctx:
            security.get_current_user(credentials=None)
        self.assertEqual(ctx.exception.status_code, 401)

        event = self.audit_logs.list_all()[-1]
        self.assertEqual(event["action"], "auth.access.unauthenticated")
        self.assertIsNone(event["user_id"])
        self.assertEqual(event["result"], "denied")

    def test_record_unauthenticated_event_helper(self):
        audit_auth_unauthenticated(reason="missing_or_invalid_scheme")
        event = self.audit_logs.list_all()[-1]
        self.assertEqual(event["metadata"]["reason"], "missing_or_invalid_scheme")


class MetadataSanitizationTests(unittest.TestCase):
    def test_sensitive_keys_are_removed(self):
        sanitized = sanitize_metadata(
            {
                "username": "analyst",
                "password": "secret-pass",
                "access_token": "jwt-token",
                "nested": {"secret": "value", "role": "ANALYST"},
            }
        )
        self.assertEqual(
            sanitized,
            {"username": "analyst", "nested": {"role": "ANALYST"}},
        )

    def test_record_event_sanitizes_metadata(self):
        repository = InMemoryAuditRepository()
        set_audit_repository(repository)
        try:
            record_audit_event(
                user_id=None,
                action="auth.login.failure",
                resource_type="user",
                result="failure",
                metadata={"username": "analyst", "password": "secret"},
            )
            event = repository.list_all()[-1]
            self.assertNotIn("password", event["metadata"])
            self.assertEqual(event["metadata"]["username"], "analyst")
        finally:
            set_audit_repository(None)


class AppendOnlyBehaviorTests(unittest.TestCase):
    def test_repository_exposes_append_only_interface(self):
        repository = InMemoryAuditRepository()
        self.assertTrue(hasattr(repository, "append"))
        self.assertFalse(hasattr(repository, "update_by_id"))
        self.assertFalse(hasattr(repository, "delete"))

    def test_postgres_repository_protocol_is_append_only(self):
        repository = InMemoryAuditRepository()
        self.assertTrue(callable(getattr(repository, "append", None)))
        self.assertFalse(hasattr(repository, "update_by_id"))
        self.assertFalse(hasattr(repository, "delete"))


class AuditFailurePolicyTests(AuditTestCase):
    def test_required_audit_failure_blocks_login_success(self):
        set_audit_repository(FailingAuditRepository())
        with self.assertRaises(HTTPException) as ctx:
            auth_api.post_login({"username": "analyst", "password": "analyst-pass"})
        self.assertEqual(ctx.exception.status_code, 503)

    def test_required_audit_failure_blocks_investigation_create_success(self):
        set_audit_repository(FailingAuditRepository())
        with self.assertRaises(HTTPException) as ctx:
            investigations_api.post_investigation(
                {"name": "Should fail audit"},
                current_user=self.analyst,
            )
        self.assertEqual(ctx.exception.status_code, 503)

    def test_record_event_raises_audit_write_error_when_required(self):
        set_audit_repository(FailingAuditRepository())
        with self.assertRaises(AuditWriteError):
            audit_auth_login_success(self.analyst)

    def test_record_event_can_be_non_required(self):
        set_audit_repository(FailingAuditRepository())
        event = record_audit_event(
            user_id=None,
            action="auth.login.failure",
            resource_type="user",
            result="failure",
            required=False,
        )
        self.assertEqual(event["action"], "auth.login.failure")


if __name__ == "__main__":
    unittest.main()
