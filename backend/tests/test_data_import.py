"""Tests for the data-import vertical slice."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.security import authorize_roles  # noqa: E402
from app.api.cases import list_cases, sort_case_records  # noqa: E402
from app.api.entities import get_persons  # noqa: E402
from app.services.audit_repository import (  # noqa: E402
    InMemoryAuditRepository,
    set_repository as set_audit_repository,
)
from app.services.auth import hash_password  # noqa: E402
from app.api.network import get_network_graph  # noqa: E402
from app.services.import_overlay import (  # noqa: E402
    DEFAULT_OVERLAY_DIR,
    append_overlay_rows,
    configure_overlay,
    load_overlay_from_disk,
    overlay_rows,
    reset_overlay,
)
from app.services.import_parsing import ImportParseError, parse_structured_upload  # noqa: E402
from app.services.import_schema import apply_user_mappings, suggest_mappings  # noqa: E402
from app.services.import_service import (  # noqa: E402
    ImportAccessDenied,
    ImportValidationError,
    assert_write_role,
    canonical_crime,
    confirm_import,
    import_entry_options,
    inspect_manual_record,
    inspect_upload,
    list_imports_for_user,
    reset_crime_canonical_cache,
    validate_import,
)
from app.services.import_store import reset_import_store  # noqa: E402
from app.services.ingestion import load_fir, load_persons  # noqa: E402
from app.services.review_repository import (  # noqa: E402
    InMemoryReviewRepository,
    set_repository as set_review_repository,
)
from app.services.user_repository import (  # noqa: E402
    InMemoryUserRepository,
    set_repository as set_user_repository,
)
from fastapi import HTTPException  # noqa: E402


def _utc() -> str:
    return "2026-01-01T00:00:00+00:00"


class DataImportTests(unittest.TestCase):
    def setUp(self):
        configure_overlay(directory=DEFAULT_OVERLAY_DIR, persist=False)
        reset_overlay()
        reset_import_store()
        reset_crime_canonical_cache()
        self.users = InMemoryUserRepository()
        self.audit = InMemoryAuditRepository()
        self.reviews = InMemoryReviewRepository()
        set_user_repository(self.users)
        set_audit_repository(self.audit)
        set_review_repository(self.reviews)

        self.admin = self.users.insert(
            {
                "id": str(uuid.uuid4()),
                "username": "admin",
                "password_hash": hash_password("admin-pass"),
                "role": "ADMIN",
                "jurisdictions": [],
                "created_at": _utc(),
            }
        )
        self.analyst = self.users.insert(
            {
                "id": str(uuid.uuid4()),
                "username": "analyst-del",
                "password_hash": hash_password("analyst-pass"),
                "role": "ANALYST",
                "jurisdictions": ["DEL"],
                "created_at": _utc(),
            }
        )
        self.viewer = self.users.insert(
            {
                "id": str(uuid.uuid4()),
                "username": "viewer",
                "password_hash": hash_password("viewer-pass"),
                "role": "VIEWER",
                "jurisdictions": ["MUM"],
                "created_at": _utc(),
            }
        )

    def tearDown(self):
        reset_overlay()
        configure_overlay(directory=DEFAULT_OVERLAY_DIR, persist=False)
        reset_import_store()
        set_user_repository(None)
        set_audit_repository(None)
        set_review_repository(None)

    def _inspect_csv(self, user: dict, body: str, name: str = "cases.csv"):
        return inspect_upload(
            user=user,
            filename=name,
            payload=body.encode("utf-8"),
            content_type="text/csv",
            source_kind="structured",
        )

    def test_schema_detection_maps_external_headers(self):
        suggestions = suggest_mappings(
            [
                "Case Number",
                "Suspect Name",
                "Mobile No.",
                "District",
                "Vehicle Registration",
                "Incident Date",
                "Officer",
                "Weapon",
                "Notes",
            ]
        )
        by_column = {item["column"]: item for item in suggestions}
        self.assertEqual(by_column["Case Number"]["cnas_field"], "fir_id")
        self.assertEqual(by_column["Suspect Name"]["cnas_field"], "name")
        self.assertEqual(by_column["Mobile No."]["cnas_field"], "phone")
        self.assertEqual(by_column["District"]["cnas_field"], "jurisdiction")
        self.assertEqual(by_column["Vehicle Registration"]["cnas_field"], "vehicle_no")
        self.assertEqual(by_column["Incident Date"]["cnas_field"], "date")
        self.assertIsNone(by_column["Officer"]["cnas_field"])
        self.assertIsNone(by_column["Weapon"]["cnas_field"])
        self.assertIsNone(by_column["Notes"]["cnas_field"])
        self.assertIn("retained as source data", by_column["Officer"]["notice"])

    def test_unknown_fields_survive_user_mapping_override(self):
        mappings = apply_user_mappings(
            ["Officer", "Suspect Name"],
            {"Suspect Name": "name", "Officer": None},
        )
        self.assertEqual(mappings[1]["cnas_field"], "name")
        self.assertIsNone(mappings[0]["cnas_field"])

    def test_missing_and_malformed_and_unknown_fields(self):
        csv = (
            "Case Number,Suspect Name,Mobile No.,District,Officer\n"
            "FIR-A1,Neela Shah,9876543210,DEL,Insp. Rao\n"
            ",,not-a-phone,DEL,\n"
            "FIR-A2,Neela Shah,9876543210,DEL,Kept\n"
        )
        batch = self._inspect_csv(self.analyst, csv)
        validated = validate_import(user=self.analyst, import_id=batch["id"])
        summary = validated["validation"]
        self.assertEqual(summary["detected"], 3)
        self.assertGreaterEqual(summary["ready"], 1)
        self.assertGreaterEqual(summary["incomplete"] + summary["invalid"], 1)
        rows = {row["index"]: row for row in validated["preview_rows"]}
        self.assertIn("Officer", rows[0]["unmapped"])
        self.assertEqual(rows[0]["unmapped"]["Officer"], "Insp. Rao")

    def test_duplicate_detection_within_file_and_existing_fir(self):
        csv = (
            "Case Number,Suspect Name,District\n"
            "FIR00001,Unique Import Person,DEL\n"
            "FIR-NEW-9,Zarna Quell,DEL\n"
            "FIR-NEW-9,Zarna Quell,DEL\n"
        )
        batch = self._inspect_csv(self.analyst, csv)
        validated = validate_import(user=self.analyst, import_id=batch["id"])
        statuses = [row["status"] for row in validated["preview_rows"]]
        self.assertIn("duplicate", statuses)
        self.assertEqual(validated["validation"]["duplicates"], 2)

    def test_possible_match_is_not_auto_merged(self):
        csv = "Suspect Name,District,Mobile No.\nRajesh Kumar,DEL,9000010001\n"
        batch = self._inspect_csv(self.analyst, csv)
        validated = validate_import(user=self.analyst, import_id=batch["id"])
        row = validated["preview_rows"][0]
        self.assertEqual(row["status"], "possible_duplicate")
        result = confirm_import(
            user=self.analyst,
            import_id=batch["id"],
            continue_with_warnings=True,
            include_ner=False,
            dry_run_graph=True,
        )
        imported_person = (result["result"]["provenance"]["records"][0])["person_id"]
        self.assertFalse(imported_person.startswith("P001"))
        self.assertNotEqual(imported_person, "P001")

    def test_authorization_viewer_cannot_upload(self):
        with self.assertRaises(ImportAccessDenied):
            assert_write_role(self.viewer)
        with self.assertRaises(HTTPException) as raised:
            authorize_roles(self.viewer, "ADMIN", "ANALYST", resource_type="data_import")
        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(raised.exception.detail, "Insufficient permissions")

    def test_cross_jurisdiction_records_are_blocked_and_redacted(self):
        csv = (
            "Case Number,Suspect Name,District\n"
            "FIR-DEL-1,Local Person,DEL\n"
            "FIR-MUM-1,Outside Person,Mumbai\n"
        )
        batch = self._inspect_csv(self.analyst, csv)
        validated = validate_import(user=self.analyst, import_id=batch["id"])
        summary = validated["validation"]
        self.assertEqual(summary["unauthorized"], 1)
        self.assertTrue(summary["blocking_unauthorized"])
        self.assertIn("outside your current access", summary["unauthorized_message"])
        outside = next(
            row for row in validated["preview_rows"] if row["status"] == "unauthorized"
        )
        self.assertTrue(outside["redacted"])
        self.assertEqual(outside["mapped"], {})
        with self.assertRaises(ImportValidationError):
            confirm_import(
                user=self.analyst,
                import_id=batch["id"],
                include_ner=False,
                dry_run_graph=True,
            )
        result = confirm_import(
            user=self.analyst,
            import_id=batch["id"],
            skip_indexes=[outside["index"]],
            include_ner=False,
            dry_run_graph=True,
        )
        self.assertGreaterEqual(result["result"]["imported"], 1)
        self.assertGreaterEqual(result["result"]["skipped"], 1)

    def test_admin_may_import_other_jurisdiction(self):
        csv = "Case Number,Suspect Name,District\nFIR-MUM-ADM,Admin Import,MUM\n"
        batch = self._inspect_csv(self.admin, csv)
        validated = validate_import(user=self.admin, import_id=batch["id"])
        self.assertEqual(validated["validation"]["unauthorized"], 0)
        result = confirm_import(
            user=self.admin,
            import_id=batch["id"],
            include_ner=False,
            dry_run_graph=True,
        )
        self.assertEqual(result["result"]["imported"], 1)

    def test_partial_import_keeps_successes(self):
        csv = (
            "Case Number,Suspect Name,District,Mobile No.\n"
            "FIR-OK-1,Good Person,DEL,9876500001\n"
            ",,,not-a-phone\n"
            "FIR-OK-2,Second Person,DEL,9876500002\n"
        )
        batch = self._inspect_csv(self.analyst, csv)
        validated = validate_import(user=self.analyst, import_id=batch["id"])
        skip = [
            row["index"]
            for row in validated["preview_rows"]
            if not row.get("importable")
        ]
        result = confirm_import(
            user=self.analyst,
            import_id=batch["id"],
            skip_indexes=skip,
            include_ner=False,
            dry_run_graph=True,
        )
        self.assertEqual(result["result"]["imported"], 2)
        self.assertGreaterEqual(result["result"]["skipped"], 1)
        persons = load_persons()
        names = set(persons["name"].astype(str))
        self.assertIn("Good Person", names)
        self.assertIn("Second Person", names)

    def test_provenance_and_status_and_overlay(self):
        csv = (
            "Case Number,Suspect Name,District,Officer,Notes\n"
            "FIR-PROV-1,Provenance Person,DEL,Insp. Nair,Keep this note\n"
        )
        batch = self._inspect_csv(self.analyst, csv, name="field-kit.csv")
        result = confirm_import(
            user=self.analyst,
            import_id=batch["id"],
            include_ner=False,
            dry_run_graph=True,
        )
        self.assertIn(result["status"], {"complete", "completed_with_warnings"})
        provenance = result["result"]["provenance"]
        self.assertEqual(provenance["source_file"], "field-kit.csv")
        self.assertEqual(provenance["import_id"], batch["id"])
        self.assertEqual(provenance["uploader_username"], "analyst-del")
        self.assertIn("Officer", provenance["records"][0]["unmapped"])
        self.assertIn("Notes", provenance["records"][0]["unmapped"])
        self.assertTrue(any(row.get("_import_id") == batch["id"] for row in overlay_rows("persons")))
        firs = load_fir()
        self.assertIn("FIR-PROV-1", set(firs["fir_id"].astype(str)))
        history = list_imports_for_user(self.analyst)
        self.assertEqual(history["total"], 1)
        self.assertEqual(history["data"][0]["status"], result["status"])

    def test_unstructured_text_reuses_ingestion_contract(self):
        text = (
            "FIR DEL-NAR-1. Accused Ravi Mehta of Delhi used vehicle DL5CAB9999 "
            "and phone 9988776655 during the incident."
        )
        batch = inspect_upload(
            user=self.admin,
            filename="note.txt",
            payload=text.encode("utf-8"),
            content_type="text/plain",
            source_kind="unstructured",
            jurisdiction="DEL",
        )
        self.assertEqual(batch["kind"], "unstructured")
        result = confirm_import(
            user=self.admin,
            import_id=batch["id"],
            include_ner=False,
            dry_run_graph=True,
        )
        self.assertGreaterEqual(result["result"]["imported"], 1)

    def test_unsupported_format_explains_accepted_types(self):
        with self.assertRaises(ImportParseError) as raised:
            parse_structured_upload(
                filename="scan.pdf",
                payload=b"%PDF-fake",
                content_type="application/pdf",
            )
        self.assertIn("CSV", str(raised.exception))
        self.assertIn("JSON", str(raised.exception))

    def test_json_and_excel_structured_parse(self):
        payload = json.dumps(
            [
                {
                    "Case Number": "FIR-JSON-1",
                    "Suspect Name": "Json Person",
                    "District": "DEL",
                }
            ]
        ).encode("utf-8")
        parsed = parse_structured_upload(
            filename="rows.json",
            payload=payload,
            content_type="application/json",
        )
        self.assertEqual(parsed["row_count"], 1)
        self.assertEqual(parsed["format"], "json")

        try:
            import pandas as pd
        except ImportError:
            self.skipTest("pandas missing")
        buffer = io.BytesIO()
        pd.DataFrame(
            [{"Case Number": "FIR-XLS-1", "Suspect Name": "Excel Person", "District": "DEL"}]
        ).to_excel(buffer, index=False, engine="openpyxl")
        excel = parse_structured_upload(
            filename="rows.xlsx",
            payload=buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertEqual(excel["format"], "xlsx")
        self.assertEqual(excel["row_count"], 1)

    def test_history_is_scoped_to_uploader(self):
        csv = "Suspect Name,District\nSolo Person,DEL\n"
        self._inspect_csv(self.analyst, csv)
        other = list_imports_for_user(self.admin)
        # admin sees all drafts
        self.assertGreaterEqual(other["total"], 1)
        viewer_list = list_imports_for_user(self.viewer)
        self.assertEqual(viewer_list["total"], 0)

    def test_all_duplicate_records_are_unresolved_until_explicitly_skipped(self):
        csv = (
            "Case Number,Suspect Name,District\n"
            "FIR00001,Dup One,DEL\n"
            "FIR00003,Dup Two,DEL\n"
            "FIR00004,Dup Three,DEL\n"
        )
        persons_before = len(load_persons())
        batch = self._inspect_csv(self.analyst, csv, name="all-dupes.csv")
        validated = validate_import(user=self.analyst, import_id=batch["id"])
        self.assertEqual(validated["validation"]["duplicates"], 3)
        self.assertTrue(validated["validation"]["blocking_unresolved"])
        with self.assertRaises(ImportValidationError) as raised:
            confirm_import(
                user=self.analyst,
                import_id=batch["id"],
                include_ner=False,
                dry_run_graph=True,
            )
        self.assertIn("still require a decision", str(raised.exception))
        self.assertEqual(len(load_persons()), persons_before)

        indexes = [row["index"] for row in validated["preview_rows"]]
        with patch("app.services.import_service.import_cnas_graph") as graph_import:
            result = confirm_import(
                user=self.analyst,
                import_id=batch["id"],
                skip_indexes=indexes,
                include_ner=False,
                dry_run_graph=True,
            )
            graph_import.assert_not_called()

        self.assertEqual(result["status"], "completed_with_warnings")
        payload = result["result"]
        self.assertEqual(payload["imported"], 0)
        self.assertEqual(payload["skipped"], 3)
        self.assertEqual(payload["failed"], 0)
        self.assertIn("all records were skipped", payload["notice"])
        self.assertEqual(len(payload["skipped_rows"]), 3)
        self.assertTrue(
            any("already exists" in " ".join(row["reasons"]) for row in payload["skipped_rows"])
        )
        self.assertEqual(len(load_persons()), persons_before)
        history = list_imports_for_user(self.analyst)
        self.assertEqual(history["data"][0]["imported"], 0)
        self.assertEqual(history["data"][0]["skipped"], 3)
        self.assertEqual(history["data"][0]["status"], "completed_with_warnings")

    def test_all_records_manually_skipped_completes_without_import(self):
        csv = (
            "Case Number,Suspect Name,District\n"
            "FIR-SKIP-A,Manual Skip A,DEL\n"
            "FIR-SKIP-B,Manual Skip B,DEL\n"
        )
        batch = self._inspect_csv(self.analyst, csv)
        validated = validate_import(user=self.analyst, import_id=batch["id"])
        indexes = [row["index"] for row in validated["preview_rows"]]
        self.assertGreaterEqual(len(indexes), 2)
        with patch("app.services.import_service.import_cnas_graph") as graph_import:
            result = confirm_import(
                user=self.analyst,
                import_id=batch["id"],
                skip_indexes=indexes,
                include_ner=False,
                dry_run_graph=True,
            )
            graph_import.assert_not_called()

        payload = result["result"]
        self.assertEqual(result["status"], "completed_with_warnings")
        self.assertEqual(payload["imported"], 0)
        self.assertEqual(payload["skipped"], len(indexes))
        self.assertEqual(payload["failed"], 0)
        self.assertTrue(
            all(row["status"] == "skipped" for row in payload["skipped_rows"])
        )
        history = list_imports_for_user(self.analyst)
        self.assertEqual(history["data"][0]["imported"], 0)
        self.assertEqual(history["data"][0]["skipped"], len(indexes))

    def test_mixed_importable_and_skipped_still_imports_ready_rows(self):
        csv = (
            "Case Number,Suspect Name,District\n"
            "FIR00001,Existing Case,DEL\n"
            "FIR-MIX-NEW,Fresh Person,DEL\n"
        )
        batch = self._inspect_csv(self.analyst, csv)
        validated = validate_import(user=self.analyst, import_id=batch["id"])
        duplicate = next(
            row for row in validated["preview_rows"] if row["status"] == "duplicate"
        )
        with self.assertRaises(ImportValidationError):
            confirm_import(
                user=self.analyst,
                import_id=batch["id"],
                include_ner=False,
                dry_run_graph=True,
            )
        result = confirm_import(
            user=self.analyst,
            import_id=batch["id"],
            skip_indexes=[duplicate["index"]],
            include_ner=False,
            dry_run_graph=True,
        )
        payload = result["result"]
        self.assertGreaterEqual(payload["imported"], 1)
        self.assertGreaterEqual(payload["skipped"], 1)
        self.assertIn("Fresh Person", set(load_persons()["name"].astype(str)))
        self.assertNotIn(
            "Existing Case",
            {row.get("name") for row in overlay_rows("persons")},
        )

    def test_graph_unavailable_is_warning_not_success(self):
        csv = (
            "Case Number,Suspect Name,District\n"
            "FIR-GRAPH-UNAVAIL,Graph Gap Person,DEL\n"
        )
        batch = self._inspect_csv(self.analyst, csv, name="graph-gap.csv")
        with patch(
            "app.services.import_service.import_cnas_graph",
            return_value={
                "status": "unavailable",
                "detail": "Neo4j environment variables are not configured",
                "nodes": 2,
                "relationships": 1,
            },
        ):
            result = confirm_import(
                user=self.analyst,
                import_id=batch["id"],
                include_ner=False,
                dry_run_graph=False,
            )

        self.assertEqual(result["status"], "completed_with_warnings")
        payload = result["result"]
        self.assertGreaterEqual(payload["imported"], 1)
        self.assertGreaterEqual(payload["warnings"], 1)
        self.assertEqual(payload["graph"]["status"], "unavailable")
        self.assertIsNotNone(payload["graph"]["warning"])
        self.assertIn("unavailable", payload["graph"]["warning"].lower())
        self.assertIn("retry graph import", payload["graph"]["warning"].lower())
        self.assertEqual(payload["stage_results"]["graph_import"], "unavailable")
        self.assertNotIn("graph_import", result["stages"])
        self.assertIn("complete", result["stages"])
        persons = load_persons()
        self.assertIn("Graph Gap Person", set(persons["name"].astype(str)))
        firs = load_fir()
        self.assertIn("FIR-GRAPH-UNAVAIL", set(firs["fir_id"].astype(str)))

    def test_graph_failed_keeps_people_and_does_not_mark_graph_complete(self):
        csv = (
            "Case Number,Suspect Name,District\n"
            "FIR-GRAPH-FAIL,Graph Fail Person,DEL\n"
        )
        batch = self._inspect_csv(self.analyst, csv)
        with patch(
            "app.services.import_service.import_cnas_graph",
            return_value={
                "status": "failed",
                "detail": "connection refused",
                "nodes": 2,
                "relationships": 1,
            },
        ):
            result = confirm_import(
                user=self.analyst,
                import_id=batch["id"],
                include_ner=False,
                dry_run_graph=False,
            )

        self.assertEqual(result["status"], "completed_with_warnings")
        payload = result["result"]
        self.assertGreaterEqual(payload["imported"], 1)
        self.assertEqual(payload["graph"]["status"], "failed")
        self.assertEqual(payload["stage_results"]["graph_import"], "failed")
        self.assertNotEqual(payload["stage_results"]["graph_import"], "complete")
        self.assertGreaterEqual(payload["warnings"], 1)
        self.assertTrue(
            any(item["status"] == "failed" for item in payload["warning_reasons"])
        )
        self.assertIn("Graph Fail Person", set(load_persons()["name"].astype(str)))

    def test_successful_graph_import_is_complete_without_graph_warning(self):
        csv = (
            "Case Number,Suspect Name,District\n"
            "FIR-GRAPH-OK,Graph Ok Person,DEL\n"
        )
        batch = self._inspect_csv(self.analyst, csv)
        with patch(
            "app.services.import_service.import_cnas_graph",
            return_value={
                "status": "imported",
                "nodes": 3,
                "relationships": 2,
            },
        ):
            result = confirm_import(
                user=self.analyst,
                import_id=batch["id"],
                include_ner=False,
                dry_run_graph=False,
            )

        self.assertEqual(result["status"], "complete")
        payload = result["result"]
        self.assertEqual(payload["warnings"], 0)
        self.assertIsNone(payload["graph"]["warning"])
        self.assertEqual(payload["graph"]["status"], "imported")
        self.assertEqual(payload["stage_results"]["graph_import"], "complete")
        self.assertIn("graph_import", result["stages"])

    def test_csv_and_manual_confirm_use_the_same_graph_import_path(self):
        captured: list[dict] = []

        def capture_import(**kwargs):
            captured.append(kwargs)
            plan = kwargs.get("plan")
            return {
                "status": "imported",
                "nodes": len(plan.nodes) if plan is not None else 0,
                "relationships": len(plan.relationships) if plan is not None else 0,
            }

        csv = (
            "Case Number,Suspect Name,District,Location\n"
            "FIR-GRAPH-CSV,Graph Csv Person,DEL,Delhi\n"
        )
        csv_batch = self._inspect_csv(self.analyst, csv, name="graph-csv.csv")
        json_payload = json.dumps(
            [
                {
                    "fir_id": "FIR-GRAPH-JSON",
                    "name": "Graph Json Person",
                    "jurisdiction": "DEL",
                    "location": "Delhi",
                }
            ]
        ).encode("utf-8")
        json_batch = inspect_upload(
            user=self.analyst,
            filename="graph.json",
            payload=json_payload,
            content_type="application/json",
            source_kind="structured",
        )
        with patch(
            "app.services.import_service.import_cnas_graph",
            side_effect=capture_import,
        ):
            csv_result = confirm_import(
                user=self.analyst,
                import_id=csv_batch["id"],
                include_ner=False,
                dry_run_graph=False,
            )
            json_result = confirm_import(
                user=self.analyst,
                import_id=json_batch["id"],
                include_ner=False,
                dry_run_graph=False,
            )
            manual_batch = inspect_manual_record(
                user=self.analyst,
                payload={
                    "fir_id": "FIR-GRAPH-MAN",
                    "name": "Graph Manual Person",
                    "location": "Delhi",
                },
            )
            manual_result = confirm_import(
                user=self.analyst,
                import_id=manual_batch["id"],
                include_ner=False,
                dry_run_graph=False,
            )

        self.assertEqual(len(captured), 3)
        self.assertEqual(csv_result["result"]["graph"]["status"], "imported")
        self.assertEqual(json_result["result"]["graph"]["status"], "imported")
        self.assertEqual(manual_result["result"]["graph"]["status"], "imported")
        self.assertIs(captured[0]["dry_run"], False)
        self.assertIs(captured[1]["dry_run"], False)
        self.assertIs(captured[2]["dry_run"], False)
        for kwargs in captured:
            plan = kwargs["plan"]
            self.assertIsNotNone(plan)
            location_keys = {
                node.key_property
                for node in plan.nodes
                if node.label == "Location"
            }
            self.assertTrue(
                not location_keys or location_keys == {"name"},
                location_keys,
            )
            person_ids = {
                node.key_value
                for node in plan.nodes
                if node.label == "Person"
            }
            self.assertTrue(person_ids)

    def test_skipping_one_row_does_not_implicitly_skip_others(self):
        csv = (
            "Case Number,Suspect Name,District\n"
            "FIR00001,Existing Case,DEL\n"
            "FIR-KEEP-1,Keep Person,DEL\n"
            "FIR-KEEP-2,Also Keep,DEL\n"
        )
        batch = self._inspect_csv(self.analyst, csv)
        validated = validate_import(user=self.analyst, import_id=batch["id"])
        duplicate = next(
            row for row in validated["preview_rows"] if row["status"] == "duplicate"
        )
        result = confirm_import(
            user=self.analyst,
            import_id=batch["id"],
            skip_indexes=[duplicate["index"]],
            include_ner=False,
            dry_run_graph=True,
        )
        payload = result["result"]
        self.assertEqual(payload["imported"], 2)
        self.assertEqual(payload["skipped"], 1)
        names = set(load_persons()["name"].astype(str))
        self.assertIn("Keep Person", names)
        self.assertIn("Also Keep", names)

    def test_unresolved_incomplete_rows_block_confirm(self):
        csv = "Case Number,Suspect Name,District\n,,\nFIR-OK-INC,Present Person,DEL\n"
        batch = self._inspect_csv(self.analyst, csv)
        with self.assertRaises(ImportValidationError) as raised:
            confirm_import(
                user=self.analyst,
                import_id=batch["id"],
                include_ner=False,
                dry_run_graph=True,
            )
        self.assertIn("still require a decision", str(raised.exception))

    def test_crime_aliases_normalize_without_merging_unrelated_names(self):
        reset_crime_canonical_cache()
        canon = canonical_crime("Cyber Bullying")
        for alias in ("cyberbullying", "cyber-bullying", "cyber bullying"):
            self.assertEqual(canonical_crime(alias), canon)
        self.assertEqual(canonical_crime("cyber crime"), "Cyber Crime")
        self.assertEqual(canonical_crime("cyber-crime"), "Cyber Crime")
        self.assertNotEqual(canonical_crime("cyberbullying"), "Cyber Crime")

    def test_manual_entry_reaches_existing_pipeline(self):
        batch = inspect_manual_record(
            user=self.analyst,
            payload={
                "fir_id": "FIR-MAN-1",
                "date": "2026-03-14",
                "crime": "cyber-bullying",
                "name": "Manual Case Person",
                "phone": "9876500099",
                "notes": "Field note from the investigator.",
                "custom_fields": [{"key": "Informant", "value": "Beat officer"}],
            },
        )
        self.assertEqual(batch["source_kind"], "manual")
        self.assertEqual(batch["kind"], "structured")
        validated = validate_import(user=self.analyst, import_id=batch["id"])
        row = validated["preview_rows"][0]
        self.assertEqual(row["mapped"]["crime"], canonical_crime("cyber-bullying"))
        self.assertEqual(row["mapped"]["date"], "2026-03-14")
        self.assertEqual(row["mapped"]["jurisdiction"], "DEL")
        self.assertEqual(row["unmapped"]["Investigator Notes"], "Field note from the investigator.")
        self.assertEqual(row["unmapped"]["Investigator"], "analyst-del")
        self.assertEqual(row["unmapped"]["Informant"], "Beat officer")
        self.assertEqual(row["unmapped"]["crime_original"], "cyber-bullying")
        result = confirm_import(
            user=self.analyst,
            import_id=batch["id"],
            include_ner=False,
            dry_run_graph=True,
        )
        payload = result["result"]
        self.assertEqual(payload["imported"], 1)
        self.assertIn("Manual Case Person", set(load_persons()["name"].astype(str)))
        self.assertIn("FIR-MAN-1", set(load_fir()["fir_id"].astype(str)))
        provenance = payload["provenance"]["records"][0]
        self.assertEqual(provenance["unmapped"]["Investigator Notes"], "Field note from the investigator.")
        self.assertEqual(provenance["original"]["crime"], canonical_crime("cyber-bullying"))

    def test_manual_incomplete_but_usable_record(self):
        batch = inspect_manual_record(
            user=self.analyst,
            payload={"name": "Only A Name"},
        )
        validated = validate_import(user=self.analyst, import_id=batch["id"])
        row = validated["preview_rows"][0]
        self.assertEqual(row["mapped"]["jurisdiction"], "DEL")
        self.assertTrue(row.get("importable"))
        result = confirm_import(
            user=self.analyst,
            import_id=batch["id"],
            continue_with_warnings=True,
            include_ner=False,
            dry_run_graph=True,
        )
        self.assertGreaterEqual(result["result"]["imported"], 1)
        self.assertIn("Only A Name", set(load_persons()["name"].astype(str)))

    def test_manual_invalid_record_is_not_imported_until_resolved(self):
        batch = inspect_manual_record(
            user=self.analyst,
            payload={"phone": "not-a-phone"},
        )
        validated = validate_import(user=self.analyst, import_id=batch["id"])
        row = validated["preview_rows"][0]
        self.assertIn(row["status"], {"incomplete", "invalid"})
        self.assertFalse(row.get("importable"))
        with self.assertRaises(ImportValidationError):
            confirm_import(
                user=self.analyst,
                import_id=batch["id"],
                continue_with_warnings=True,
                include_ner=False,
                dry_run_graph=True,
            )
        result = confirm_import(
            user=self.analyst,
            import_id=batch["id"],
            skip_indexes=[row["index"]],
            include_ner=False,
            dry_run_graph=True,
        )
        self.assertEqual(result["result"]["imported"], 0)
        self.assertEqual(result["result"]["skipped"], 1)

    def test_manual_investigator_jurisdiction_locked_server_side(self):
        with self.assertRaises(ImportAccessDenied):
            inspect_manual_record(
                user=self.analyst,
                payload={
                    "name": "Spoofed Place",
                    "jurisdiction": "MUM",
                    "investigator": "admin",
                },
            )
        options = import_entry_options(self.analyst)
        self.assertTrue(options["investigator_locked"])
        self.assertTrue(options["jurisdiction_locked"])
        self.assertEqual(options["default_jurisdiction"], "DEL")
        self.assertEqual(options["default_investigator"], "analyst-del")

    def test_admin_manual_jurisdiction_and_investigator_selection(self):
        options = import_entry_options(self.admin)
        self.assertFalse(options["investigator_locked"])
        self.assertFalse(options["jurisdiction_locked"])
        self.assertIn("MUM", options["jurisdictions"])
        usernames = {item["username"] for item in options["investigators"]}
        self.assertIn("analyst-del", usernames)
        batch = inspect_manual_record(
            user=self.admin,
            payload={
                "fir_id": "FIR-ADM-MAN",
                "name": "Admin Manual Person",
                "jurisdiction": "MUM",
                "investigator": "analyst-del",
            },
        )
        validated = validate_import(user=self.admin, import_id=batch["id"])
        row = validated["preview_rows"][0]
        self.assertEqual(row["mapped"]["jurisdiction"], "MUM")
        self.assertEqual(row["unmapped"]["Investigator"], "analyst-del")
        result = confirm_import(
            user=self.admin,
            import_id=batch["id"],
            include_ner=False,
            dry_run_graph=True,
        )
        self.assertEqual(result["result"]["imported"], 1)

    def test_manual_duplicate_and_possible_match_are_not_merged(self):
        duplicate_batch = inspect_manual_record(
            user=self.analyst,
            payload={
                "fir_id": "FIR00001",
                "name": "Dup Manual",
            },
        )
        duplicate_validated = validate_import(
            user=self.analyst, import_id=duplicate_batch["id"]
        )
        self.assertEqual(duplicate_validated["preview_rows"][0]["status"], "duplicate")
        with self.assertRaises(ImportValidationError):
            confirm_import(
                user=self.analyst,
                import_id=duplicate_batch["id"],
                include_ner=False,
                dry_run_graph=True,
            )

        match_batch = inspect_manual_record(
            user=self.analyst,
            payload={
                "name": "Rajesh Kumar",
                "phone": "9000010001",
            },
        )
        match_validated = validate_import(user=self.analyst, import_id=match_batch["id"])
        row = match_validated["preview_rows"][0]
        self.assertEqual(row["status"], "possible_duplicate")
        result = confirm_import(
            user=self.analyst,
            import_id=match_batch["id"],
            continue_with_warnings=True,
            include_ner=False,
            dry_run_graph=True,
        )
        imported_person = result["result"]["provenance"]["records"][0]["person_id"]
        self.assertNotEqual(imported_person, "P001")

    def test_multiple_manual_entries_add_remove_edit_and_mixed_validity(self):
        added = inspect_manual_record(
            user=self.analyst,
            payload={
                "records": [
                    {
                        "fir_id": "FIR-MULTI-A",
                        "name": "Draft One",
                        "date": "2026-01-15",
                    },
                    {
                        "fir_id": "FIR-MULTI-B",
                        "name": "Draft Two",
                        "date": "2026-02-15",
                    },
                ]
            },
        )
        self.assertEqual(added["row_count"], 2)

        edited = inspect_manual_record(
            user=self.analyst,
            payload={
                "records": [
                    {
                        "fir_id": "FIR-MULTI-A",
                        "name": "Edited One",
                        "date": "2026-01-15",
                        "notes": "Updated in place",
                    },
                    {
                        "phone": "not-a-phone",
                    },
                    {
                        "fir_id": "FIR-MULTI-C",
                        "name": "Added Three",
                        "date": "2026-12-01",
                    },
                ]
            },
        )
        self.assertEqual(edited["row_count"], 3)
        validated = validate_import(user=self.analyst, import_id=edited["id"])
        statuses = [row["status"] for row in validated["preview_rows"]]
        self.assertIn("ready", statuses)
        self.assertTrue(any(status in {"incomplete", "invalid"} for status in statuses))
        by_index = {row["index"]: row for row in validated["preview_rows"]}
        self.assertEqual(by_index[0]["mapped"]["name"], "Edited One")
        self.assertEqual(
            by_index[0]["unmapped"]["Investigator Notes"], "Updated in place"
        )
        self.assertFalse(by_index[1].get("importable"))
        self.assertTrue(by_index[1]["reasons"])
        with self.assertRaises(ImportValidationError):
            confirm_import(
                user=self.analyst,
                import_id=edited["id"],
                include_ner=False,
                dry_run_graph=True,
            )
        result = confirm_import(
            user=self.analyst,
            import_id=edited["id"],
            skip_indexes=[1],
            include_ner=False,
            dry_run_graph=True,
        )
        self.assertEqual(result["result"]["imported"], 2)
        self.assertEqual(result["result"]["skipped"], 1)
        names = set(load_persons()["name"].astype(str))
        self.assertIn("Edited One", names)
        self.assertIn("Added Three", names)
        self.assertNotIn("Draft Two", names)

    def test_multi_manual_rbac_still_enforced(self):
        with self.assertRaises(ImportAccessDenied):
            inspect_manual_record(
                user=self.analyst,
                payload={
                    "records": [
                        {"name": "Local", "jurisdiction": "DEL"},
                        {"name": "Spoofed", "jurisdiction": "MUM"},
                    ]
                },
            )

    def test_cases_default_order_is_newest_incident_then_ingested(self):
        ordered = sort_case_records(
            [
                {
                    "fir_id": "OLD",
                    "date": "2026-01-01",
                    "_ingested_at": "2026-09-17T12:00:00+00:00",
                },
                {
                    "fir_id": "NEW-EARLY",
                    "date": "2026-12-01",
                    "_ingested_at": "2026-09-17T10:00:00+00:00",
                },
                {
                    "fir_id": "NEW-LATE",
                    "date": "2026-12-01",
                    "_ingested_at": "2026-09-17T13:00:00+00:00",
                },
            ]
        )
        self.assertEqual(
            [row["fir_id"] for row in ordered],
            ["NEW-LATE", "NEW-EARLY", "OLD"],
        )

        older = inspect_manual_record(
            user=self.analyst,
            payload={
                "fir_id": "FIR-OLD-DATE",
                "name": "Older Incident",
                "date": "2020-01-01",
            },
        )
        confirm_import(
            user=self.analyst,
            import_id=older["id"],
            include_ner=False,
            dry_run_graph=True,
        )
        newer = inspect_manual_record(
            user=self.analyst,
            payload={
                "fir_id": "FIR-NEW-DATE",
                "name": "Newer Incident",
                "date": "2026-12-31",
            },
        )
        confirm_import(
            user=self.analyst,
            import_id=newer["id"],
            include_ner=False,
            dry_run_graph=True,
        )
        cases = list_cases()
        ids = [row["fir_id"] for row in cases["data"]]
        self.assertLess(ids.index("FIR-NEW-DATE"), ids.index("FIR-OLD-DATE"))
        self.assertEqual(cases["data"][0]["fir_id"], "FIR-NEW-DATE")
        self.assertEqual(cases["data"][0]["date"], "2026-12-31")

    def test_people_api_returns_imported_persons_and_survives_reload(self):
        batch = inspect_manual_record(
            user=self.analyst,
            payload={
                "fir_id": "FIR-PEOPLE-1",
                "name": "People Page Person",
                "phone": "9876500111",
            },
        )
        confirm_import(
            user=self.analyst,
            import_id=batch["id"],
            include_ner=False,
            dry_run_graph=True,
        )
        first = get_persons()
        json.dumps(first)
        names = {row.get("name") for row in first["data"]}
        self.assertIn("People Page Person", names)
        self.assertTrue(
            all(not str(key).startswith("_") for row in first["data"] for key in row)
        )
        reload_payload = get_persons()
        json.dumps(reload_payload)
        self.assertIn(
            "People Page Person",
            {row.get("name") for row in reload_payload["data"]},
        )
        self.assertGreaterEqual(reload_payload["total"], first["total"])

    def test_people_api_stays_json_safe_after_overlay(self):
        csv = (
            "Case Number,Suspect Name,District\n"
            "FIR-JSON-SAFE,Json Safe Person,DEL\n"
        )
        batch = self._inspect_csv(self.analyst, csv)
        confirm_import(
            user=self.analyst,
            import_id=batch["id"],
            include_ner=False,
            dry_run_graph=True,
        )
        payload = get_persons()
        encoded = json.dumps(payload)
        self.assertNotIn("NaN", encoded)
        self.assertIn("Json Safe Person", encoded)

    def test_network_graph_stays_json_safe_and_includes_overlay(self):
        csv = (
            "Case Number,Suspect Name,District\n"
            "FIR-GRAPH-SAFE,Graph Safe Person,DEL\n"
        )
        batch = self._inspect_csv(self.analyst, csv)
        confirm_import(
            user=self.analyst,
            import_id=batch["id"],
            include_ner=False,
            dry_run_graph=True,
        )
        payload = get_network_graph()
        encoded = json.dumps(payload)
        self.assertNotIn("NaN", encoded)
        names = {node.get("name") for node in payload["nodes"]}
        node_ids = {str(node.get("id")) for node in payload["nodes"]}
        self.assertIn("Graph Safe Person", names)
        self.assertIn("FIR-GRAPH-SAFE", node_ids)


class OverlayPersistenceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        configure_overlay(directory=Path(self._tmp.name), persist=True)
        reset_overlay()

    def tearDown(self):
        reset_overlay()
        configure_overlay(directory=DEFAULT_OVERLAY_DIR, persist=False)
        self._tmp.cleanup()

    def test_overlay_survives_memory_reset_via_disk(self):
        append_overlay_rows(
            "persons",
            [
                {
                    "person_id": "IMP-PERSIST-1",
                    "name": "Persist Person",
                    "phone": "9876500999",
                    "_import_id": "batch-persist",
                }
            ],
        )
        append_overlay_rows(
            "fir",
            [
                {
                    "fir_id": "FIR-PERSIST-1",
                    "person_id": "IMP-PERSIST-1",
                    "crime": "Theft",
                    "_import_id": "batch-persist",
                }
            ],
        )
        reset_overlay()
        self.assertEqual(overlay_rows("persons"), [])
        self.assertEqual(overlay_rows("fir"), [])

        load_overlay_from_disk()
        person_names = {row.get("name") for row in overlay_rows("persons")}
        fir_ids = {row.get("fir_id") for row in overlay_rows("fir")}
        self.assertIn("Persist Person", person_names)
        self.assertIn("FIR-PERSIST-1", fir_ids)

        persons = load_persons()
        self.assertIn("Persist Person", set(persons["name"].astype(str)))
        self.assertGreaterEqual(len(persons), 51)

        payload = get_persons()
        json.dumps(payload)
        self.assertIn(
            "Persist Person",
            {row.get("name") for row in payload["data"]},
        )


if __name__ == "__main__":
    unittest.main()

