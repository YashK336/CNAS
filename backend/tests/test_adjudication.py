"""Tests for human adjudication workflow and audit integration."""

import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api import adjudication as adjudication_api  # noqa: E402
from app.api import audit_logs as audit_logs_api  # noqa: E402
from app.core import security  # noqa: E402
from app.services.adjudication_service import (  # noqa: E402
    AdjudicationValidationError,
    compute_review_fingerprint,
    create_review_from_resolution,
    queue_ambiguous_reviews,
)
from app.services.audit_repository import (  # noqa: E402
    InMemoryAuditRepository,
    set_repository as set_audit_repository,
)
from app.services.audit_service import AuditWriteError  # noqa: E402
from app.services.auth import hash_password  # noqa: E402
from app.services.entity_resolution import (  # noqa: E402
    CanonicalRegistry,
    build_canonical_registry,
    resolve_candidate,
)
from app.services.extraction import EntityCandidate  # noqa: E402
from app.services.resolution_config import (  # noqa: E402
    MAPPING_SOURCE_ADJUDICATION,
    METHOD_EXACT_PHONE,
    RESOLUTION_STATUS_AMBIGUOUS,
    RESOLUTION_STATUS_RESOLVED,
    RESOLUTION_STATUS_UNRESOLVED,
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


def _candidate(
    entity_type: str,
    value: str,
    record_id: str = "test:row:0",
) -> EntityCandidate:
    return EntityCandidate(
        entity_type=entity_type,
        value=value,
        normalized_value=value,
        confidence=1.0,
        source="test",
        record_id=record_id,
        start=0,
        end=len(value),
        offset=0,
        source_text=value,
        extraction_method="regex",
        resolution_eligible=True,
    )


def _ambiguous_resolution(**overrides):
    payload = {
        "candidate_value": "+919000010099",
        "entity_type": "phone",
        "matched_entity_id": None,
        "confidence": 1.0,
        "method": METHOD_EXACT_PHONE,
        "status": RESOLUTION_STATUS_AMBIGUOUS,
        "proposed_entity_ids": ["P100", "P101"],
        "candidate_scores": {"P100": 1.0, "P101": 1.0},
        "ambiguity_reason": "Exact phone identifier matched 2 canonical entities.",
    }
    payload.update(overrides)
    return payload


class AdjudicationTestCase(unittest.TestCase):
    def setUp(self):
        self.users = InMemoryUserRepository()
        self.reviews = InMemoryReviewRepository()
        self.audit_logs = InMemoryAuditRepository()
        set_user_repository(self.users)
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
        self.viewer_del = self.users.insert(
            {
                "id": str(uuid.uuid4()),
                "username": "viewer-del",
                "password_hash": hash_password("viewer-pass"),
                "role": "VIEWER",
                "jurisdictions": ["DEL"],
                "created_at": _utc_now_iso(),
            }
        )
        self.analyst_mum = self.users.insert(
            {
                "id": str(uuid.uuid4()),
                "username": "analyst-mum",
                "password_hash": hash_password("analyst-pass"),
                "role": "ANALYST",
                "jurisdictions": ["MUM"],
                "created_at": _utc_now_iso(),
            }
        )

        self.settings_patch = patch(
            "app.core.security.jwt_settings",
            return_value=JWT_SETTINGS,
        )
        self.settings_patch.start()
        self.graph_import_patch = patch(
            "app.services.graph.importer.import_cnas_graph",
            return_value={"status": "unavailable"},
        )
        self.graph_import_patch.start()

        from app.services.import_overlay import configure_overlay, reset_overlay

        configure_overlay(persist=False)
        reset_overlay()

    def tearDown(self):
        from app.services.import_overlay import configure_overlay, reset_overlay

        reset_overlay()
        configure_overlay(persist=False)
        self.graph_import_patch.stop()
        self.settings_patch.stop()
        set_user_repository(None)
        set_review_repository(None)
        set_audit_repository(None)

    def _create_pending_review(self, *, jurisdiction: str = "DEL") -> dict:
        review = create_review_from_resolution(
            result=_ambiguous_resolution(),
            jurisdiction=jurisdiction,
            candidate=_candidate("phone", "+919000010099"),
        )
        assert review is not None
        return review


class ReviewCreationTests(AdjudicationTestCase):
    def test_ambiguous_resolution_creates_pending_review(self):
        review = self._create_pending_review()
        self.assertEqual(review["status"], "pending")
        self.assertEqual(review["proposed_entity_ids"], ["P100", "P101"])
        self.assertEqual(review["matching_method"], METHOD_EXACT_PHONE)
        self.assertEqual(review["jurisdiction"], "DEL")

    def test_queue_ambiguous_reviews_from_registry(self):
        registry = CanonicalRegistry()
        registry.phones["+919000010099"] = {"P100", "P101"}

        _, queued = queue_ambiguous_reviews(
            [_candidate("phone", "+919000010099")],
            jurisdiction="DEL",
            registry=registry,
        )

        self.assertEqual(len(queued), 1)
        self.assertEqual(queued[0]["status"], "pending")

    def test_duplicate_review_is_not_created(self):
        first = self._create_pending_review()
        second = self._create_pending_review()
        self.assertEqual(first["review_id"], second["review_id"])
        self.assertEqual(len(self.reviews.list_pending()), 1)

    def test_malformed_ambiguous_resolution_is_rejected(self):
        with self.assertRaises(AdjudicationValidationError):
            create_review_from_resolution(
                result=_ambiguous_resolution(proposed_entity_ids=[]),
                jurisdiction="DEL",
            )


class ReviewRetrievalTests(AdjudicationTestCase):
    def test_list_pending_reviews_for_jurisdiction(self):
        self._create_pending_review(jurisdiction="DEL")
        self._create_pending_review(jurisdiction="MUM")

        listing = adjudication_api.get_pending_reviews(current_user=self.analyst_del)
        self.assertEqual(listing["total"], 1)
        self.assertEqual(listing["reviews"][0]["jurisdiction"], "DEL")

    def test_admin_sees_all_pending_reviews(self):
        self._create_pending_review(jurisdiction="DEL")
        self._create_pending_review(jurisdiction="MUM")

        listing = adjudication_api.get_pending_reviews(current_user=self.admin)
        self.assertEqual(listing["total"], 2)

    def test_get_review_detail(self):
        review = self._create_pending_review()
        detail = adjudication_api.get_review_by_id(
            review["review_id"],
            current_user=self.analyst_del,
        )
        self.assertEqual(detail["review_id"], review["review_id"])
        self.assertIn("ambiguity_reason", detail)


class ReviewDecisionTests(AdjudicationTestCase):
    def test_confirm_review_records_reviewer_and_audit(self):
        review = self._create_pending_review()
        confirmed = adjudication_api.post_confirm_review(
            review["review_id"],
            {"canonical_entity_id": "P100", "reason": "Strongest corroboration"},
            current_user=self.analyst_del,
        )
        self.assertEqual(confirmed["status"], "confirmed")
        self.assertEqual(confirmed["reviewer_id"], self.analyst_del["id"])
        self.assertEqual(confirmed["confirmed_entity_id"], "P100")

        actions = [event["action"] for event in self.audit_logs.list_all()]
        self.assertIn("adjudication.review.confirm", actions)

    def test_reject_review_registers_rejection_and_audit(self):
        review = self._create_pending_review()
        rejected = adjudication_api.post_reject_review(
            review["review_id"],
            {"reason": "Distinct persons"},
            current_user=self.analyst_del,
        )
        self.assertEqual(rejected["status"], "rejected")
        self.assertEqual(rejected["reviewer_id"], self.analyst_del["id"])

        fingerprint = compute_review_fingerprint(
            candidate_value=review["candidate_value"],
            entity_type=review["entity_type"],
            proposed_entity_ids=review["proposed_entity_ids"],
            matching_method=review["matching_method"],
            jurisdiction=review["jurisdiction"],
        )
        self.assertTrue(self.reviews.is_rejected(fingerprint))

        actions = [event["action"] for event in self.audit_logs.list_all()]
        self.assertIn("adjudication.review.reject", actions)

    def test_rejection_prevents_silent_remerge(self):
        review = self._create_pending_review()
        adjudication_api.post_reject_review(
            review["review_id"],
            {"reason": "Keep separate"},
            current_user=self.analyst_del,
        )

        registry = CanonicalRegistry()
        registry.phones["+919000010099"] = {"P100", "P101"}
        result = resolve_candidate(
            _candidate("phone", "+919000010099"),
            registry,
            jurisdiction="DEL",
        )

        self.assertEqual(result["status"], RESOLUTION_STATUS_UNRESOLVED)
        self.assertIsNone(result["matched_entity_id"])
        self.assertIn("resolution_note", result)

    def test_confirm_applies_canonical_id_to_mapping_and_resolution(self):
        from app.services.import_overlay import overlay_rows

        review = self._create_pending_review()
        confirmed = adjudication_api.post_confirm_review(
            review["review_id"],
            {"canonical_entity_id": "P100"},
            current_user=self.analyst_del,
        )
        self.assertEqual(confirmed["status"], "confirmed")
        self.assertEqual(confirmed["confirmed_entity_id"], "P100")

        mapping = overlay_rows("entity_mapping")
        self.assertEqual(len(mapping), 1)
        self.assertEqual(mapping[0]["entity_id"], "P100")
        self.assertEqual(mapping[0]["entity_type"], "phone")
        self.assertEqual(mapping[0]["source"], MAPPING_SOURCE_ADJUDICATION)
        self.assertEqual(mapping[0]["source_id"], "+919000010099")

        registry = build_canonical_registry()
        registry.phones["+919000010099"] = {"P100", "P101"}
        result = resolve_candidate(
            _candidate("phone", "+919000010099"),
            registry,
            jurisdiction="DEL",
        )
        self.assertEqual(result["status"], RESOLUTION_STATUS_RESOLVED)
        self.assertEqual(result["matched_entity_id"], "P100")
        self.assertEqual(result.get("resolution_note"), "Human reviewer confirmed this canonical entity.")

        from app.services.graph.mapper import map_entity_mapping_records
        from app.services.normalization import normalize_row
        import pandas as pd

        record = normalize_row(
            "entity_mapping",
            pd.Series(
                {
                    "entity_id": mapping[0]["entity_id"],
                    "entity_type": mapping[0]["entity_type"],
                    "source": mapping[0]["source"],
                    "source_id": mapping[0]["source_id"],
                }
            ),
            0,
        )
        plan = map_entity_mapping_records([record], registry=registry)
        self.assertTrue(
            any(rel.rel_type == "HAS_PHONE" and rel.from_value == "P100" for rel in plan.relationships)
        )

    def test_confirm_requires_proposed_entity_id(self):
        from app.services.import_overlay import overlay_rows

        review = self._create_pending_review()
        with self.assertRaises(HTTPException) as ctx:
            adjudication_api.post_confirm_review(
                review["review_id"],
                {"canonical_entity_id": "P999"},
                current_user=self.analyst_del,
            )
        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(overlay_rows("entity_mapping"), [])
        pending = adjudication_api.get_pending_reviews(current_user=self.analyst_del)
        self.assertEqual(pending["total"], 1)


class AuthorizationTests(AdjudicationTestCase):
    def test_viewer_cannot_confirm_or_reject(self):
        review = self._create_pending_review()
        with self.assertRaises(HTTPException) as ctx:
            adjudication_api.post_confirm_review(
                review["review_id"],
                {"canonical_entity_id": "P100"},
                current_user=self.viewer_del,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_cross_jurisdiction_read_is_denied(self):
        review = self._create_pending_review(jurisdiction="DEL")
        with self.assertRaises(HTTPException) as ctx:
            adjudication_api.get_review_by_id(
                review["review_id"],
                current_user=self.analyst_mum,
            )
        self.assertEqual(ctx.exception.status_code, 403)

        event = self.audit_logs.list_all()[-1]
        self.assertEqual(event["action"], "adjudication.review.read")
        self.assertEqual(event["result"], "denied")

    def test_cross_jurisdiction_confirm_is_denied(self):
        review = self._create_pending_review(jurisdiction="DEL")
        with self.assertRaises(HTTPException) as ctx:
            adjudication_api.post_confirm_review(
                review["review_id"],
                {"canonical_entity_id": "P100"},
                current_user=self.analyst_mum,
            )
        self.assertEqual(ctx.exception.status_code, 403)


class PersistenceFailureTests(AdjudicationTestCase):
    def test_confirm_fails_when_review_store_unavailable(self):
        review = self._create_pending_review()
        self.reviews._fail_on_update = True
        with self.assertRaises(RuntimeError):
            adjudication_api.post_confirm_review(
                review["review_id"],
                {"canonical_entity_id": "P100"},
                current_user=self.analyst_del,
            )

    def test_list_pending_succeeds_when_audit_store_unavailable(self):
        self._create_pending_review()

        class FailingAuditRepository:
            def ensure_schema(self):
                return None

            def append(self, record):
                raise RuntimeError("audit store unavailable")

            def list_events(self, *, limit=100, offset=0):
                return []

        set_audit_repository(FailingAuditRepository())
        listing = adjudication_api.get_pending_reviews(current_user=self.analyst_del)
        self.assertEqual(listing["total"], 1)


class AuditLogReadTests(AdjudicationTestCase):
    def test_audit_log_list_returns_sanitized_events(self):
        review = self._create_pending_review()
        adjudication_api.post_confirm_review(
            review["review_id"],
            {"canonical_entity_id": "P100"},
            current_user=self.analyst_del,
        )
        listing = audit_logs_api.get_audit_logs(
            limit=100,
            offset=0,
            current_user=self.admin,
        )
        self.assertGreaterEqual(listing["total"], 1)
        event = listing["events"][0]
        self.assertIn("actor_username", event)
        self.assertIn("metadata", event)
        self.assertNotIn("password", event["metadata"])
        actions = [entry["action"] for entry in self.audit_logs.list_all()]
        self.assertNotIn("audit.log.list", actions)

    def test_audit_log_list_is_jurisdiction_scoped_for_non_admin(self):
        review_del = self._create_pending_review(jurisdiction="DEL")
        review_mum = self._create_pending_review(jurisdiction="MUM")
        adjudication_api.post_confirm_review(
            review_del["review_id"],
            {"canonical_entity_id": "P100"},
            current_user=self.analyst_del,
        )
        adjudication_api.post_confirm_review(
            review_mum["review_id"],
            {"canonical_entity_id": "P100"},
            current_user=self.admin,
        )

        listing = audit_logs_api.get_audit_logs(
            limit=100,
            offset=0,
            current_user=self.analyst_del,
        )
        jurisdictions = {
            event["jurisdiction"]
            for event in listing["events"]
            if event.get("jurisdiction") is not None
        }
        self.assertTrue(jurisdictions.issubset({"DEL"}))


class EvaluateEndpointTests(AdjudicationTestCase):
    def test_evaluate_queues_ambiguous_candidates(self):
        registry = CanonicalRegistry()
        registry.phones["+919000010099"] = {"P100", "P101"}

        with patch(
            "app.services.adjudication_service.build_canonical_registry",
            return_value=registry,
        ):
            response = adjudication_api.post_evaluate_candidates(
                {
                    "candidates": [_candidate("phone", "+919000010099")],
                    "jurisdiction": "DEL",
                },
                current_user=self.analyst_del,
            )

        self.assertEqual(response["queued_total"], 1)
        self.assertEqual(response["resolution_results"][0]["status"], RESOLUTION_STATUS_AMBIGUOUS)

    def test_seed_name_import_queues_then_confirm_and_reject(self):
        from app.services.entity_resolution import (
            build_canonical_registry,
            resolve_candidate,
        )
        from app.services.import_overlay import configure_overlay, reset_overlay
        from app.services.import_service import confirm_import, inspect_upload, validate_import
        from app.services.import_store import reset_import_store
        from app.services.ingestion import load_persons

        try:
            configure_overlay(persist=False)
            reset_overlay()
            reset_import_store()
            persons_before = len(load_persons())

            kumar_csv = b"Case Number,Suspect Name,District\nFIR-AMB-KUMAR,Kumar,DEL\n"
            kumar_batch = inspect_upload(
                user=self.analyst_del,
                filename="kumar.csv",
                payload=kumar_csv,
                content_type="text/csv",
                source_kind="structured",
            )
            kumar_row = validate_import(
                user=self.analyst_del, import_id=kumar_batch["id"]
            )["preview_rows"][0]
            self.assertEqual(kumar_row["status"], "possible_duplicate")
            self.assertTrue((kumar_row.get("possible_match") or {}).get("ambiguous"))

            kumar_result = confirm_import(
                user=self.analyst_del,
                import_id=kumar_batch["id"],
                continue_with_warnings=True,
                include_ner=False,
                dry_run_graph=True,
            )
            self.assertGreaterEqual(kumar_result["result"]["queued_reviews"], 1)

            sharma_csv = b"Case Number,Suspect Name,District\nFIR-AMB-SHARMA,Sharma,DEL\n"
            sharma_batch = inspect_upload(
                user=self.analyst_del,
                filename="sharma.csv",
                payload=sharma_csv,
                content_type="text/csv",
                source_kind="structured",
            )
            sharma_result = confirm_import(
                user=self.analyst_del,
                import_id=sharma_batch["id"],
                continue_with_warnings=True,
                include_ner=False,
                dry_run_graph=True,
            )
            self.assertGreaterEqual(sharma_result["result"]["queued_reviews"], 1)

            listing = adjudication_api.get_pending_reviews(current_user=self.analyst_del)
            kumar_review = next(
                row for row in listing["reviews"] if row["candidate_value"] == "Kumar"
            )
            sharma_review = next(
                row for row in listing["reviews"] if row["candidate_value"] == "Sharma"
            )

            confirmed = adjudication_api.post_confirm_review(
                kumar_review["review_id"],
                {"canonical_entity_id": kumar_review["proposed_entity_ids"][0]},
                current_user=self.analyst_del,
            )
            self.assertEqual(confirmed["status"], "confirmed")
            self.assertEqual(
                confirmed["confirmed_entity_id"],
                kumar_review["proposed_entity_ids"][0],
            )

            registry = build_canonical_registry()
            after_confirm = resolve_candidate(
                _candidate("person_name", "Kumar"),
                registry,
                jurisdiction="DEL",
            )
            self.assertEqual(after_confirm["status"], RESOLUTION_STATUS_RESOLVED)
            self.assertEqual(
                after_confirm["matched_entity_id"],
                kumar_review["proposed_entity_ids"][0],
            )

            rejected = adjudication_api.post_reject_review(
                sharma_review["review_id"],
                {"reason": "Keep separate"},
                current_user=self.analyst_del,
            )
            self.assertEqual(rejected["status"], "rejected")
            after_reject = resolve_candidate(
                _candidate("person_name", "Sharma"),
                registry,
                jurisdiction="DEL",
            )
            self.assertEqual(after_reject["status"], RESOLUTION_STATUS_UNRESOLVED)

            self.assertEqual(len(load_persons()), persons_before + 2)
        finally:
            reset_overlay()
            configure_overlay(persist=False)

    def test_evaluate_rejects_malformed_candidates(self):
        with self.assertRaises(HTTPException) as ctx:
            adjudication_api.post_evaluate_candidates(
                {"candidates": [{"value": "missing-fields"}]},
                current_user=self.analyst_del,
            )
        self.assertEqual(ctx.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
