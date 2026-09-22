"""Contract and migration coverage for the SUTRADHAAR ontology projection."""

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.graph.importer import apply_constraints  # noqa: E402
from app.services.graph.mapper import build_cnas_graph_plan  # noqa: E402
from app.services.graph.ontology import (  # noqa: E402
    CANONICAL_RELATIONSHIP_TYPES,
    MANDATORY_EDGE_PROVENANCE_FIELDS,
    validate_edge_provenance,
)


class CanonicalContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = build_cnas_graph_plan()
        cls.contract = cls.plan.to_contract()

    def test_contract_uses_documented_shape_and_available_node_types(self):
        self.assertTrue(self.contract["nodes"])
        self.assertTrue(self.contract["edges"])
        self.assertTrue({"id", "type", "properties", "confidence", "source_refs"}.issubset(self.contract["nodes"][0]))
        self.assertTrue({"id", "type", "from", "to", "properties"}.issubset(self.contract["edges"][0]))
        node_types = {node["type"] for node in self.contract["nodes"]}
        self.assertTrue({"Person", "Phone", "Vehicle", "Account", "Location", "Case", "Incident"}.issubset(node_types))

    def test_contract_edges_use_only_documented_relationships_and_provenance(self):
        for edge in self.contract["edges"]:
            self.assertIn(edge["type"], CANONICAL_RELATIONSHIP_TYPES)
            self.assertTrue(edge["source_ref"])
            self.assertTrue(edge["extraction_method"])
            self.assertEqual(set(MANDATORY_EDGE_PROVENANCE_FIELDS), {
                field for field in edge if field in MANDATORY_EDGE_PROVENANCE_FIELDS
            })

    def test_missing_required_provenance_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_edge_provenance({"source_ref": "record-1"})

    def test_constraint_migration_includes_legacy_and_canonical_labels(self):
        session = type("Session", (), {"run": lambda self, query: None})()
        self.assertEqual(apply_constraints(session), 13)


if __name__ == "__main__":
    unittest.main()
