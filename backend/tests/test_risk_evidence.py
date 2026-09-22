"""Tests for risk evidence chains."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import risk_evidence  # noqa: E402
from app.services.neo4j_analytics import Neo4jUnavailableError, PersonNotFoundError  # noqa: E402


class RiskEvidenceTests(unittest.TestCase):
    def test_requires_graph_seeds(self):
        with self.assertRaises(ValueError):
            risk_evidence.get_risk_graph_evidence("P002", [])

    @patch("app.services.risk_evidence.query_person_path")
    def test_returns_path_evidence_with_full_provenance(self, mock_query_path):
        mock_query_path.return_value = {
            "found": True,
            "nodes": [
                {
                    "id": "P001",
                    "labels": ["Person"],
                    "properties": {"person_id": "P001", "name": "Alice"},
                },
                {
                    "id": "P002",
                    "labels": ["Person"],
                    "properties": {"person_id": "P002", "name": "Bob"},
                },
            ],
            "relationships": [
                {
                    "type": "CALLED",
                    "source": "P001",
                    "target": "P002",
                    "properties": {
                        "source": "cdr",
                        "source_ref": "cdr:P001:P002:2026-01-01",
                        "content_hash": "abc123",
                        "ingested_at": "2026-01-01T00:00:00+00:00",
                    },
                    "provenance": {
                        "source": "cdr",
                        "source_ref": "cdr:P001:P002:2026-01-01",
                        "content_hash": "abc123",
                        "ingested_at": "2026-01-01T00:00:00+00:00",
                    },
                }
            ],
        }

        result = risk_evidence.get_risk_graph_evidence("P002", ["P001"])

        chain = result["evidence"]["graph_propagation"][0]
        self.assertTrue(chain["found"])
        self.assertEqual(chain["degrees_of_separation"], 1)
        self.assertEqual(chain["relationships"][0]["type"], "CALLED")
        self.assertEqual(chain["relationships"][0]["provenance"]["content_hash"], "abc123")
        self.assertEqual(chain["relationships"][0]["provenance"]["ingested_at"], "2026-01-01T00:00:00+00:00")
        mock_query_path.assert_called_once_with("P001", "P002", max_depth=6)

    @patch("app.services.risk_evidence.query_person_path")
    def test_does_not_invent_evidence_when_no_path(self, mock_query_path):
        mock_query_path.return_value = {
            "found": False,
            "message": "No path between the selected persons",
            "nodes": [],
            "relationships": [],
        }

        result = risk_evidence.get_risk_graph_evidence("P010", ["P001"])

        chain = result["evidence"]["graph_propagation"][0]
        self.assertFalse(chain["found"])
        self.assertEqual(chain["relationships"], [])
        self.assertEqual(chain["nodes"], [])

    @patch("app.services.risk_evidence.query_person_path")
    def test_seed_person_returns_zero_hop_evidence(self, mock_query_path):
        result = risk_evidence.get_risk_graph_evidence("P001", ["P001"])

        chain = result["evidence"]["graph_propagation"][0]
        self.assertTrue(chain["found"])
        self.assertTrue(chain["is_seed_person"])
        self.assertEqual(chain["degrees_of_separation"], 0)
        mock_query_path.assert_not_called()

    @patch("app.services.risk_evidence.query_person_path")
    def test_neo4j_unavailable_returns_empty_chain(self, mock_query_path):
        mock_query_path.side_effect = Neo4jUnavailableError("unavailable")

        result = risk_evidence.get_risk_graph_evidence("P002", ["P001"])

        chain = result["evidence"]["graph_propagation"][0]
        self.assertFalse(chain["found"])
        self.assertEqual(chain["relationships"], [])


class RiskEvidenceEndpointTests(unittest.TestCase):
    @patch("app.api.analytics.get_risk_graph_evidence")
    @patch("app.api.analytics.build_criminal_network")
    def test_evidence_endpoint(self, mock_graph, mock_evidence):
        import networkx as nx

        from app.api.analytics import get_person_risk_evidence

        graph = nx.MultiDiGraph()
        graph.add_node("P002", entity_type="person", name="Bob")
        mock_graph.return_value = graph
        mock_evidence.return_value = {
            "entity_id": "P002",
            "graph_seeds": ["P001"],
            "evidence": {"graph_propagation": []},
        }

        result = get_person_risk_evidence(
            person_id="P002",
            graph_seeds="P001",
            max_depth=4,
        )

        self.assertEqual(result["entity_id"], "P002")
        mock_evidence.assert_called_once_with("P002", ["P001"], max_depth=4)

    @patch("app.api.analytics.build_criminal_network")
    def test_evidence_endpoint_returns_404_for_unknown_person(self, mock_graph):
        import networkx as nx

        from app.api.analytics import get_person_risk_evidence
        from fastapi import HTTPException

        mock_graph.return_value = nx.MultiDiGraph()

        with self.assertRaises(HTTPException) as ctx:
            get_person_risk_evidence(person_id="P999", graph_seeds="P001")

        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
