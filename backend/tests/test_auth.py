"""Tests for authentication, JWT validation, and RBAC."""

import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api import auth as auth_api  # noqa: E402
from app.api import investigations as investigations_api  # noqa: E402
from app.core import security  # noqa: E402
from app.services.auth import (  # noqa: E402
    authenticate_user,
    hash_password,
    verify_password,
)
from app.services.audit_repository import (  # noqa: E402
    InMemoryAuditRepository,
    set_repository as set_audit_repository,
)
from app.services.investigation_repository import (  # noqa: E402
    InMemoryInvestigationRepository,
    set_repository as set_investigation_repository,
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


class AuthTestCase(unittest.TestCase):
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

    def tearDown(self):
        self.settings_patch.stop()
        set_user_repository(None)
        set_investigation_repository(None)
        set_audit_repository(None)


class PasswordHashingTests(AuthTestCase):
    def test_hash_and_verify_password(self):
        password_hash = hash_password("correct horse battery staple")
        self.assertNotEqual(password_hash, "correct horse battery staple")
        self.assertTrue(verify_password("correct horse battery staple", password_hash))
        self.assertFalse(verify_password("wrong-password", password_hash))


class JwtValidationTests(AuthTestCase):
    def test_create_and_decode_access_token(self):
        token = security.create_access_token(self.analyst)
        payload = security.decode_access_token(token)
        self.assertEqual(payload["sub"], self.analyst["id"])
        self.assertEqual(payload["role"], "ANALYST")

    def test_decode_rejects_tampered_token(self):
        token = security.create_access_token(self.analyst)
        with self.assertRaises(security.AuthenticationError):
            security.decode_access_token(token + "tampered")

    def test_decode_rejects_expired_token(self):
        expired_settings = {
            **JWT_SETTINGS,
            "expire_minutes": -1,
        }
        with patch("app.core.security.jwt_settings", return_value=expired_settings):
            token = security.create_access_token(self.analyst)
        with self.assertRaises(security.AuthenticationError):
            security.decode_access_token(token)


class MissingTokenTests(AuthTestCase):
    def test_get_current_user_rejects_missing_token(self):
        with self.assertRaises(HTTPException) as ctx:
            security.get_current_user(credentials=None)
        self.assertEqual(ctx.exception.status_code, 401)


class LoginEndpointTests(AuthTestCase):
    def test_login_returns_jwt_for_valid_credentials(self):
        response = auth_api.post_login(
            {"username": "analyst", "password": "analyst-pass"}
        )
        self.assertEqual(response["token_type"], "bearer")
        self.assertTrue(response["access_token"])
        self.assertEqual(response["user"]["username"], "analyst")
        self.assertEqual(response["user"]["role"], "ANALYST")
        self.assertNotIn("password_hash", response["user"])

    def test_login_rejects_invalid_credentials(self):
        with self.assertRaises(HTTPException) as ctx:
            auth_api.post_login({"username": "analyst", "password": "wrong"})
        self.assertEqual(ctx.exception.status_code, 401)


class CurrentUserEndpointTests(AuthTestCase):
    def test_me_returns_public_user_profile(self):
        profile = auth_api.get_me(current_user=self.viewer)
        self.assertEqual(profile["username"], "viewer")
        self.assertEqual(profile["role"], "VIEWER")
        self.assertNotIn("password_hash", profile)


class InvestigationRbacTests(AuthTestCase):
    def test_analyst_can_create_and_update_investigations(self):
        created = investigations_api.post_investigation(
            {"name": "Analyst trace", "selected_entity_ids": ["P001"]},
            current_user=self.analyst,
        )
        self.assertEqual(created["created_by"], self.analyst["id"])

        updated = investigations_api.put_investigation(
            created["id"],
            {"name": "Updated trace"},
            current_user=self.analyst,
        )
        self.assertEqual(updated["name"], "Updated trace")

    def test_viewer_can_read_but_not_write(self):
        created = investigations_api.post_investigation(
            {"name": "Seed trace", "jurisdiction": "DEL"},
            current_user=self.admin,
        )

        listing = investigations_api.get_investigations(current_user=self.viewer)
        self.assertEqual(listing["total"], 1)

        fetched = investigations_api.get_investigation_by_id(
            created["id"],
            current_user=self.viewer,
        )
        self.assertEqual(fetched["name"], "Seed trace")

        with self.assertRaises(HTTPException) as ctx:
            investigations_api.post_investigation(
                {"name": "Blocked"},
                current_user=self.viewer,
            )
        self.assertEqual(ctx.exception.status_code, 403)

        with self.assertRaises(HTTPException) as ctx:
            investigations_api.put_investigation(
                created["id"],
                {"name": "Blocked"},
                current_user=self.viewer,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_analyst_cannot_update_another_users_investigation(self):
        created = investigations_api.post_investigation(
            {"name": "Admin trace", "jurisdiction": "DEL"},
            current_user=self.admin,
        )

        with self.assertRaises(HTTPException) as ctx:
            investigations_api.put_investigation(
                created["id"],
                {"name": "Blocked"},
                current_user=self.analyst,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_admin_can_update_any_investigation(self):
        created = investigations_api.post_investigation(
            {"name": "Analyst trace"},
            current_user=self.analyst,
        )

        updated = investigations_api.put_investigation(
            created["id"],
            {"name": "Admin override"},
            current_user=self.admin,
        )
        self.assertEqual(updated["name"], "Admin override")

    def test_legacy_investigation_without_created_by_is_admin_only(self):
        legacy = self.investigations.insert(
            {
                "id": str(uuid.uuid4()),
                "name": "Legacy trace",
                "description": None,
                "selected_entity_ids": ["P010"],
                "graph_seeds": [],
                "from_datetime": None,
                "to_datetime": None,
                "created_by": None,
                "jurisdiction": None,
                "created_at": _utc_now_iso(),
                "updated_at": _utc_now_iso(),
            }
        )

        with self.assertRaises(HTTPException) as ctx:
            investigations_api.get_investigation_by_id(
                legacy["id"],
                current_user=self.viewer,
            )
        self.assertEqual(ctx.exception.status_code, 403)

        fetched = investigations_api.get_investigation_by_id(
            legacy["id"],
            current_user=self.admin,
        )
        self.assertIsNone(fetched["created_by"])
        self.assertIsNone(fetched["jurisdiction"])


class AuthenticateUserTests(AuthTestCase):
    def test_authenticate_user_returns_record_for_valid_credentials(self):
        user = authenticate_user("admin", "admin-pass")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "admin")

    def test_authenticate_user_returns_none_for_invalid_password(self):
        self.assertIsNone(authenticate_user("admin", "wrong"))


if __name__ == "__main__":
    unittest.main()
