"""Tests for unstructured FIR graph mapping and import."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.entity_resolution import (  # noqa: E402
    CanonicalRegistry,
    build_canonical_registry,
)
from app.services.extraction import EntityCandidate  # noqa: E402
from app.services.extraction_config import (  # noqa: E402
    EXTRACTION_METHOD_NER,
    EXTRACTION_METHOD_REGEX,
)
from app.services.graph.mapper import build_cnas_graph_plan  # noqa: E402
from app.services.graph.ontology import (  # noqa: E402
    LABEL_FIR,
    LABEL_PERSON,
    LABEL_PHONE,
    LABEL_VEHICLE,
    MANDATORY_EDGE_PROVENANCE_FIELDS,
    REL_CO_ACCUSED_IN,
    REL_HAS_PHONE,
    REL_INVOLVED_IN,
    REL_OWNS,
    REL_USES,
    validate_edge_provenance,
)
from app.services.ner_extraction import NerSpan, set_ner_extractor  # noqa: E402
from app.services.resolution_config import (  # noqa: E402
    RESOLUTION_STATUS_AMBIGUOUS,
    RESOLUTION_STATUS_RESOLVED,
    RESOLUTION_STATUS_UNRESOLVED,
)
from app.services.review_repository import (  # noqa: E402
    InMemoryReviewRepository,
    set_repository as set_review_repository,
)
from app.services.unstructured_graph_mapping import (  # noqa: E402
    build_unstructured_fir_graph_plan,
    import_unstructured_fir_graph,
    map_resolved_unstructured_fir,
)
from app.services.unstructured_ingestion import ingest_unstructured_fir  # noqa: E402

FIXED_TIME = "2026-01-01T00:00:00+00:00"
SOURCE_REF = "FIR-DEL-2026-0042"
JURISDICTION = "DEL"

FIR_NARRATIVE = (
    "FIR DEL/2026/0042 dated 08-09-2026. Complainant Priya Verma met Rahul Sharma "
    "near Sector 21 Bus Stand in Mumbai. Suspect phone +91-90000-10001 and vehicle DL11AB1001."
)


class StaticNerExtractor:
    def __init__(self, spans: list[NerSpan]):
        self.spans = spans

    def extract(self, text: str) -> list[NerSpan]:
        return [
            span
            for span in self.spans
            if 0 <= span.start < span.end <= len(text)
            and text[span.start : span.end] == span.source_text
        ]


def _candidate(
    entity_type: str,
    value: str,
    *,
    extraction_method: str = EXTRACTION_METHOD_REGEX,
    record_id: str = "unstructured_fir:FIR-DEL-2026-0042",
    confidence: float = 1.0,
) -> EntityCandidate:
    return EntityCandidate(
        entity_type=entity_type,
        value=value,
        normalized_value=value,
        confidence=confidence,
        source="unstructured_fir",
        record_id=record_id,
        start=0,
        end=len(value),
        offset=0,
        source_text=value,
        extraction_method=extraction_method,
        resolution_eligible=True,
    )


def _ingest(text: str = FIR_NARRATIVE) -> dict:
    return ingest_unstructured_fir(
        {
            "source": "unstructured_fir",
            "source_ref": SOURCE_REF,
            "jurisdiction": JURISDICTION,
            "text": text,
        },
        ingested_at=FIXED_TIME,
    )


def setUpModule():
    set_review_repository(InMemoryReviewRepository())


def tearDownModule():
    set_review_repository(None)


class UnstructuredGraphMappingTests(unittest.TestCase):
    def setUp(self):
        text = FIR_NARRATIVE
        self.spans = [
            NerSpan("person", text[52:63], 0.97, 52, 63, text[52:63]),
            NerSpan("person", text[68:80], 0.96, 68, 80, text[68:80]),
            NerSpan("location", text[86:105], 0.91, 86, 105, text[86:105]),
            NerSpan("location", text[109:115], 0.90, 109, 115, text[109:115]),
        ]
        set_ner_extractor(StaticNerExtractor(self.spans))
        self.record = _ingest(text)

    def tearDown(self):
        set_ner_extractor(None)

    def test_resolved_unstructured_fir_creates_expected_graph_entities(self):
        result = build_unstructured_fir_graph_plan(self.record)
        labels = {node.label for node in result.plan.nodes}
        rel_types = {rel.rel_type for rel in result.plan.relationships}

        self.assertIn(LABEL_FIR, labels)
        self.assertIn(LABEL_PERSON, labels)
        self.assertIn(LABEL_PHONE, labels)
        self.assertIn(LABEL_VEHICLE, labels)
        self.assertIn(REL_HAS_PHONE, rel_types)
        self.assertIn(REL_OWNS, rel_types)
        self.assertIn(REL_INVOLVED_IN, rel_types)
        self.assertIn(REL_USES, rel_types)
        self.assertIn(REL_CO_ACCUSED_IN, rel_types)
        self.assertGreaterEqual(len(result.resolved), 2)

    def test_existing_canonical_entities_are_reused(self):
        result = build_unstructured_fir_graph_plan(self.record)
        person_ids = {
            node.key_value
            for node in result.plan.nodes
            if node.label == LABEL_PERSON
        }
        self.assertIn("P001", person_ids)
        self.assertTrue(all(person_id.startswith("P") for person_id in person_ids))

    def test_provenance_present_on_every_generated_relationship(self):
        result = build_unstructured_fir_graph_plan(self.record)

        self.assertTrue(result.plan.relationships)
        for relationship in result.plan.relationships:
            for field in MANDATORY_EDGE_PROVENANCE_FIELDS:
                self.assertIn(field, relationship.properties)
            validate_edge_provenance(relationship.properties)

    def test_extraction_method_is_regex_or_ner(self):
        result = build_unstructured_fir_graph_plan(self.record)
        methods = {
            (item[0]["entity_type"], item[0]["extraction_method"])
            for item in result.resolved
        }
        rel_methods = {rel.properties["extraction_method"] for rel in result.plan.relationships}

        self.assertIn(("phone", EXTRACTION_METHOD_REGEX), methods)
        self.assertIn(("vehicle", EXTRACTION_METHOD_REGEX), methods)
        self.assertTrue(rel_methods.issubset({EXTRACTION_METHOD_REGEX, EXTRACTION_METHOD_NER}))

        phone_rel = next(rel for rel in result.plan.relationships if rel.rel_type == REL_HAS_PHONE)
        self.assertEqual(phone_rel.properties["extraction_method"], EXTRACTION_METHOD_REGEX)

    def test_source_ref_and_jurisdiction_propagate(self):
        result = build_unstructured_fir_graph_plan(self.record)

        for relationship in result.plan.relationships:
            self.assertEqual(relationship.properties["source_ref"], SOURCE_REF)
            self.assertEqual(relationship.properties["jurisdiction"], JURISDICTION)
            self.assertEqual(relationship.properties["ingested_at"], FIXED_TIME)

        fir_node = next(node for node in result.plan.nodes if node.label == LABEL_FIR)
        self.assertEqual(fir_node.key_value, SOURCE_REF)

    def test_ambiguous_and_unresolved_candidates_are_not_merged(self):
        registry = build_canonical_registry()
        registry.phones["+919000010099"] = {"P100", "P101"}

        text = (
            "Suspect phone +91-90000-10001 and disputed phone +91-90000-10099 "
            "plus unknown phone +919999999999."
        )
        record = _ingest(text)
        result = build_unstructured_fir_graph_plan(
            record,
            registry=registry,
            include_ner=False,
        )

        skipped_statuses = {item[1]["status"] for item in result.skipped}
        self.assertIn(RESOLUTION_STATUS_AMBIGUOUS, skipped_statuses)
        self.assertIn(RESOLUTION_STATUS_UNRESOLVED, skipped_statuses)

        person_ids = {
            rel.from_value
            for rel in result.plan.relationships
            if rel.rel_type == REL_INVOLVED_IN
        }
        self.assertEqual(person_ids, {"P001"})

    def test_reingesting_same_fir_is_idempotent(self):
        first = build_unstructured_fir_graph_plan(self.record)
        second = build_unstructured_fir_graph_plan(self.record)

        first_edge_ids = sorted(rel.record_id for rel in first.plan.relationships)
        second_edge_ids = sorted(rel.record_id for rel in second.plan.relationships)
        self.assertEqual(first_edge_ids, second_edge_ids)
        self.assertEqual(first.summary(), second.summary())

    def test_ambiguous_candidate_queues_review_without_graph_merge(self):
        registry = CanonicalRegistry()
        registry.phones["+919000010099"] = {"P100", "P101"}
        candidate = _candidate("phone", "+919000010099")
        record = _ingest("Shared phone +91-90000-10099 was observed.")

        from app.services.entity_resolution import resolve_candidate

        resolution = resolve_candidate(candidate, registry, jurisdiction=JURISDICTION)
        self.assertEqual(resolution["status"], RESOLUTION_STATUS_AMBIGUOUS)

        from app.services.graph.mapper import GraphPlan

        plan = GraphPlan()
        map_resolved_unstructured_fir(
            plan,
            record,
            [(candidate, resolution)],
            registry=registry,
        )
        self.assertEqual(plan.relationships, [])

        result = build_unstructured_fir_graph_plan(
            record,
            registry=registry,
            include_ner=False,
            queue_reviews=True,
        )
        self.assertGreaterEqual(len(result.queued_reviews), 1)
        self.assertEqual(result.plan.relationships, [])


class UnstructuredGraphImportTests(unittest.TestCase):
    def test_import_dry_run_does_not_require_driver(self):
        record = _ingest("Suspect phone +91-90000-10001 only.")
        with patch("app.services.unstructured_graph_mapping.import_cnas_graph") as mock_import:
            mock_import.return_value = {"status": "dry_run", "nodes": 1, "relationships": 1}
            result = import_unstructured_fir_graph(record, dry_run=True, include_ner=False)

        self.assertEqual(result["status"], "dry_run")
        mock_import.assert_called_once()

    def test_structured_graph_plan_unchanged(self):
        structured = build_cnas_graph_plan()
        self.assertGreater(structured.summary()["nodes"], 0)
        self.assertGreater(structured.summary()["relationships"], 0)


class UnstructuredGraphProvenanceFailureTests(unittest.TestCase):
    def test_incomplete_edge_provenance_is_rejected(self):
        from app.services.graph.mapper import GraphPlan, RelationshipSpec

        with self.assertRaises(ValueError):
            validate_edge_provenance({"source_ref": SOURCE_REF})


if __name__ == "__main__":
    unittest.main()
