"""Tests for CNAS investigation/case report export."""

import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api import cases as cases_api  # noqa: E402
from app.api import investigations as investigations_api  # noqa: E402
from app.services.adjudication_service import create_review_from_resolution  # noqa: E402
from app.services.audit_repository import (  # noqa: E402
    InMemoryAuditRepository,
    set_repository as set_audit_repository,
)
from app.services.auth import hash_password  # noqa: E402
from app.services.import_overlay import configure_overlay, reset_overlay  # noqa: E402
from app.services.investigation_repository import (  # noqa: E402
    InMemoryInvestigationRepository,
    set_repository as set_investigation_repository,
)
from app.services.report_pdf import render_investigation_report_pdf  # noqa: E402
from app.services.resolution_config import (  # noqa: E402
    METHOD_EXACT_PHONE,
    RESOLUTION_STATUS_AMBIGUOUS,
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
from fastapi.responses import Response  # noqa: E402

JWT_SETTINGS = {
    "secret": "test-secret-key",
    "algorithm": "HS256",
    "expire_minutes": 30,
}


def _utc_now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


class ReportTestCase(unittest.TestCase):
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

        self.settings_patch = patch(
            "app.core.security.jwt_settings",
            return_value=JWT_SETTINGS,
        )
        self.settings_patch.start()
        configure_overlay(persist=False)
        reset_overlay()

    def tearDown(self):
        reset_overlay()
        configure_overlay(persist=False)
        self.settings_patch.stop()
        set_user_repository(None)
        set_investigation_repository(None)
        set_review_repository(None)
        set_audit_repository(None)

    def _create_investigation(self, **overrides):
        payload = {
            "name": "DEL trace",
            "selected_entity_ids": ["P001"],
            "graph_seeds": ["P001"],
            "jurisdiction": "DEL",
        }
        payload.update(overrides)
        return investigations_api.post_investigation(
            payload,
            current_user=self.analyst_del,
        )


class InvestigationReportTests(ReportTestCase):
    def test_json_report_includes_existing_case_people_and_analytics(self):
        created = self._create_investigation()
        payload = investigations_api.get_investigation_report(
            created["id"],
            format="json",
            current_user=self.analyst_del,
        )

        self.assertEqual(payload["source"]["type"], "investigation")
        self.assertEqual(payload["source"]["id"], created["id"])
        self.assertEqual(payload["jurisdiction"], "DEL")
        self.assertEqual(payload["investigator"]["username"], "analyst-del")
        self.assertTrue(payload["generated_at"])
        self.assertTrue(payload["cases"])
        self.assertTrue(any(case["person_id"] == "P001" for case in payload["cases"]))
        self.assertTrue(any(person["person_id"] == "P001" for person in payload["people"]))
        self.assertTrue(payload["analytics"]["risk"])
        self.assertEqual(payload["an2_findings"], [])
        self.assertIn("limitations", payload)
        self.assertIn("evidence", payload)
        self.assertIn("confidence", payload)
        self.assertFalse(
            any("guilty" in str(note).lower() for note in payload["limitations"])
        )

        actions = [event["action"] for event in self.audit_logs.list_all()]
        self.assertIn("investigation.report.export", actions)

    def test_pdf_report_is_downloadable_pdf(self):
        created = self._create_investigation()
        response = investigations_api.get_investigation_report(
            created["id"],
            format="pdf",
            current_user=self.analyst_del,
        )
        self.assertIsInstance(response, Response)
        self.assertEqual(response.media_type, "application/pdf")
        self.assertTrue(response.body.startswith(b"%PDF"))
        self.assertIn(b"CNAS INVESTIGATION REPORT", response.body)
        self.assertIn(b"DEL trace", response.body)
        self.assertIn("attachment", response.headers.get("content-disposition", ""))

    def test_empty_investigation_keeps_empty_sections(self):
        created = self._create_investigation(
            selected_entity_ids=[],
            graph_seeds=[],
            name="Empty workspace",
        )
        payload = investigations_api.get_investigation_report(
            created["id"],
            format="json",
            current_user=self.analyst_del,
        )
        self.assertEqual(payload["cases"], [])
        self.assertEqual(payload["people"], [])
        self.assertEqual(payload["adjudication"], [])
        self.assertEqual(payload["an2_findings"], [])
        self.assertTrue(any("No FIR/case records" in note for note in payload["limitations"]))
        self.assertTrue(
            any("AN-2 findings were not generated" in note for note in payload["limitations"])
        )

        pdf = investigations_api.get_investigation_report(
            created["id"],
            format="pdf",
            current_user=self.analyst_del,
        )
        self.assertIn(b"None recorded.", pdf.body)

    def test_missing_investigation_returns_404(self):
        with self.assertRaises(HTTPException) as ctx:
            investigations_api.get_investigation_report(
                str(uuid.uuid4()),
                format="json",
                current_user=self.analyst_del,
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_cross_jurisdiction_export_is_denied(self):
        created = self._create_investigation()
        with self.assertRaises(HTTPException) as ctx:
            investigations_api.get_investigation_report(
                created["id"],
                format="json",
                current_user=self.analyst_mum,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_viewer_can_export_in_jurisdiction(self):
        created = self._create_investigation()
        payload = investigations_api.get_investigation_report(
            created["id"],
            format="json",
            current_user=self.viewer_del,
        )
        self.assertEqual(payload["source"]["id"], created["id"])

    def test_adjudication_decision_is_included_when_relevant(self):
        created = self._create_investigation()
        review = create_review_from_resolution(
            result={
                "candidate_value": "+919000010001",
                "entity_type": "phone",
                "matched_entity_id": None,
                "confidence": 1.0,
                "method": METHOD_EXACT_PHONE,
                "status": RESOLUTION_STATUS_AMBIGUOUS,
                "proposed_entity_ids": ["P001", "P002"],
                "candidate_scores": {"P001": 1.0, "P002": 1.0},
                "ambiguity_reason": "Exact phone identifier matched 2 canonical entities.",
            },
            jurisdiction="DEL",
        )
        self.assertIsNotNone(review)
        payload = investigations_api.get_investigation_report(
            created["id"],
            format="json",
            current_user=self.analyst_del,
        )
        self.assertTrue(
            any(item["candidate_value"] == "+919000010001" for item in payload["adjudication"])
        )


class CaseReportTests(ReportTestCase):
    def test_case_json_and_pdf_reports(self):
        payload = cases_api.get_case_report(
            "FIR00001",
            format="json",
            current_user=self.analyst_del,
        )
        self.assertEqual(payload["source"]["type"], "case")
        self.assertEqual(payload["source"]["id"], "FIR00001")
        self.assertTrue(payload["cases"])
        self.assertEqual(payload["cases"][0]["fir_id"], "FIR00001")
        self.assertTrue(any(person["person_id"] == "P001" for person in payload["people"]))

        pdf = cases_api.get_case_report(
            "FIR00001",
            format="pdf",
            current_user=self.analyst_del,
        )
        self.assertTrue(pdf.body.startswith(b"%PDF"))
        self.assertIn(b"FIR00001", pdf.body)

    def test_missing_case_report_returns_404(self):
        with self.assertRaises(HTTPException) as ctx:
            cases_api.get_case_report(
                "FIR-DOES-NOT-EXIST",
                format="json",
                current_user=self.analyst_del,
            )
        self.assertEqual(ctx.exception.status_code, 404)


class PdfLayoutTests(unittest.TestCase):
    def test_pdf_renders_every_relationship_across_pages(self):
        relationships = [
            {
                "source": f"SRC{index:03d}",
                "relationship": f"REL{index:03d}",
                "target": f"TGT{index:03d}",
            }
            for index in range(90)
        ]
        payload = {
            "report_id": "layout-test",
            "generated_at": "2026-01-01T00:00:00+00:00",
            "generated_by": {"username": "analyst", "role": "ANALYST"},
            "source": {"type": "investigation", "id": "layout-test"},
            "investigation": {"name": "Relationship pagination"},
            "investigator": {"username": "analyst", "role": "ANALYST"},
            "jurisdiction": "DEL",
            "cases": [],
            "people": [],
            "entities": {"vehicles": []},
            "network_summary": {
                "in_scope_nodes": 90,
                "in_scope_relationships": 90,
                "relationships": relationships,
                "global": {"nodes": 90, "edges": 90},
            },
            "analytics": {"risk": [], "anomalies": [], "centrality": []},
            "an2_findings": [],
            "adjudication": [],
            "evidence": [],
            "confidence": {},
            "limitations": ["This report restates recorded CNAS data."],
        }
        pdf = render_investigation_report_pdf(payload)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertIn(b"/Type /Page", pdf)
        self.assertGreaterEqual(pdf.count(b"/Type /Page"), 2)
        for index in range(90):
            self.assertIn(f"SRC{index:03d}".encode(), pdf)
            self.assertIn(f"REL{index:03d}".encode(), pdf)
            self.assertIn(f"TGT{index:03d}".encode(), pdf)


if __name__ == "__main__":
    unittest.main()
