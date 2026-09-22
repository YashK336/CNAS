"""Entity resolution tests."""

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.entity_resolution import (  # noqa: E402
    CanonicalRegistry,
    build_canonical_registry,
    resolve_candidate,
    resolve_candidates,
)
from app.services.extraction import EntityCandidate  # noqa: E402
from app.services.resolution_config import (  # noqa: E402
    METHOD_EXACT_PHONE,
    METHOD_FUZZY_NAME,
    RESOLUTION_STATUS_AMBIGUOUS,
    RESOLUTION_STATUS_RESOLVED,
    RESOLUTION_STATUS_UNRESOLVED,
)
from app.services.review_repository import (  # noqa: E402
    InMemoryReviewRepository,
    set_repository as set_review_repository,
)


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


def setUpModule():
    set_review_repository(InMemoryReviewRepository())


def tearDownModule():
    set_review_repository(None)


class ExactIdentifierTests(unittest.TestCase):
    def setUp(self):
        self.registry = build_canonical_registry()

    def test_exact_phone_match(self):
        result = resolve_candidate(
            _candidate("phone", "+919000010001"),
            self.registry,
        )

        self.assertEqual(result["status"], RESOLUTION_STATUS_RESOLVED)
        self.assertEqual(result["matched_entity_id"], "P001")
        self.assertEqual(result["method"], METHOD_EXACT_PHONE)
        self.assertEqual(result["confidence"], 1.0)

    def test_normalized_phone_match(self):
        result = resolve_candidate(
            _candidate("phone", "+91-90000-10001"),
            self.registry,
        )

        self.assertEqual(result["status"], RESOLUTION_STATUS_RESOLVED)
        self.assertEqual(result["matched_entity_id"], "P001")

    def test_exact_vehicle_match(self):
        result = resolve_candidate(
            _candidate("vehicle", "dl11ab1001"),
            self.registry,
        )

        self.assertEqual(result["status"], RESOLUTION_STATUS_RESOLVED)
        self.assertEqual(result["matched_entity_id"], "P001")

    def test_exact_bank_account_match(self):
        result = resolve_candidate(
            _candidate("bank_account", "acc100001"),
            self.registry,
        )

        self.assertEqual(result["status"], RESOLUTION_STATUS_RESOLVED)
        self.assertEqual(result["matched_entity_id"], "P001")


class NameResolutionTests(unittest.TestCase):
    def setUp(self):
        self.registry = build_canonical_registry()

    def test_confident_name_match(self):
        result = resolve_candidate(
            _candidate("person_name", "Rajesh Kumar"),
            self.registry,
        )

        self.assertEqual(result["status"], RESOLUTION_STATUS_RESOLVED)
        self.assertEqual(result["matched_entity_id"], "P001")
        self.assertEqual(result["method"], METHOD_FUZZY_NAME)
        self.assertGreaterEqual(result["confidence"], 92.0)

    def test_ambiguous_name_match(self):
        result = resolve_candidate(
            _candidate("person_name", "Kumar"),
            self.registry,
        )

        self.assertEqual(result["status"], RESOLUTION_STATUS_AMBIGUOUS)
        self.assertIsNone(result["matched_entity_id"])
        self.assertEqual(result["method"], METHOD_FUZZY_NAME)

    def test_unresolved_candidate(self):
        result = resolve_candidate(
            _candidate("phone", "+919999999999"),
            self.registry,
        )

        self.assertEqual(result["status"], RESOLUTION_STATUS_UNRESOLVED)
        self.assertIsNone(result["matched_entity_id"])

        name_result = resolve_candidate(
            _candidate("person_name", "Completely Unknown Person"),
            self.registry,
        )
        self.assertEqual(name_result["status"], RESOLUTION_STATUS_UNRESOLVED)
        self.assertIsNone(name_result["matched_entity_id"])


class AmbiguousIdentifierTests(unittest.TestCase):
    def test_ambiguous_exact_identifier(self):
        registry = CanonicalRegistry()
        registry.phones["+919000010099"] = {"P100", "P101"}

        result = resolve_candidate(
            _candidate("phone", "+919000010099"),
            registry,
        )

        self.assertEqual(result["status"], RESOLUTION_STATUS_AMBIGUOUS)
        self.assertIsNone(result["matched_entity_id"])

    def test_confirmed_mapping_overrides_ambiguous_identifier(self):
        registry = CanonicalRegistry()
        registry.phones["+919000010099"] = {"P100", "P101"}
        registry.confirmed[("phone", "+919000010099")] = "P100"

        result = resolve_candidate(
            _candidate("phone", "+919000010099"),
            registry,
        )

        self.assertEqual(result["status"], RESOLUTION_STATUS_RESOLVED)
        self.assertEqual(result["matched_entity_id"], "P100")

    def test_confirmed_name_mapping_overrides_ambiguous_name(self):
        registry = build_canonical_registry()
        registry.confirmed[("person_name", "kumar")] = "P001"

        result = resolve_candidate(
            _candidate("person_name", "Kumar"),
            registry,
        )

        self.assertEqual(result["status"], RESOLUTION_STATUS_RESOLVED)
        self.assertEqual(result["matched_entity_id"], "P001")


class BatchResolutionTests(unittest.TestCase):
    def test_multiple_candidates(self):
        candidates = [
            _candidate("phone", "+91-90000-10001", record_id="r1"),
            _candidate("vehicle", "KA12AB1002", record_id="r2"),
            _candidate("person_name", "Rajesh Kumar", record_id="r3"),
            _candidate("phone", "+919999999999", record_id="r4"),
        ]

        results = resolve_candidates(candidates)

        self.assertEqual(len(results), 4)
        self.assertEqual(results[0]["matched_entity_id"], "P001")
        self.assertEqual(results[1]["matched_entity_id"], "P002")
        self.assertEqual(results[2]["matched_entity_id"], "P001")
        self.assertEqual(results[3]["status"], RESOLUTION_STATUS_UNRESOLVED)


if __name__ == "__main__":
    unittest.main()
