"""Tests for Neo4j-backed investigation queries."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import neo4j_analytics  # noqa: E402


class _FakeNode:
    def __init__(self, labels, properties):
        self.labels = labels
        self.element_id = f"node:{properties.get('person_id') or properties.get('name')}"
        self._properties = properties

    def __iter__(self):
        return iter(self._properties.items())

    def items(self):
        return self._properties.items()

    def __getitem__(self, item):
        return self._properties[item]

    def get(self, key, default=None):
        return self._properties.get(key, default)


class _FakeRelationship:
    def __init__(self, rel_type, start_node, end_node, properties):
        self.type = rel_type
        self.start_node = start_node
        self.end_node = end_node
        self._properties = properties

    def __iter__(self):
        return iter(self._properties.items())

    def items(self):
        return self._properties.items()


class Neo4jAnalyticsQueryTests(unittest.TestCase):
    def test_normalize_relationship_types_filters_unknown_values(self):
        validated = neo4j_analytics.normalize_relationship_types(
            ["CALLED", "UNKNOWN", "OWNS"]
        )
        self.assertEqual(validated, ["CALLED", "OWNS"])

    @patch("app.services.neo4j_analytics.run_cypher")
    def test_neighborhood_uses_parameterized_cypher(self, mock_run_cypher):
        center = _FakeNode(["Person"], {"person_id": "P001", "name": "Alice"})
        target = _FakeNode(["Person"], {"person_id": "P002", "name": "Bob"})
        relationship = _FakeRelationship(
            "CALLED",
            center,
            target,
            {
                "source": "cdr",
                "source_ref": "cdr:P001:P002:2026-01-01",
                "timestamp": "2026-01-01T10:00:00",
            },
        )

        mock_run_cypher.side_effect = [
            [{"person_id": "P001"}],
            [{"nodes": [center, target], "relationships": [relationship]}],
        ]

        result = neo4j_analytics.query_person_neighborhood(
            "P001",
            max_depth=2,
            relationship_types=["CALLED"],
            from_datetime="2026-01-01",
            to_datetime="2026-12-31",
        )

        neighborhood_call = mock_run_cypher.call_args_list[1]
        cypher = neighborhood_call.args[0]
        params = neighborhood_call.args[1]

        self.assertIn("$person_id", cypher)
        self.assertIn("$max_depth", cypher)
        self.assertIn("$rel_types", cypher)
        self.assertNotIn("P001", cypher)
        self.assertEqual(params["person_id"], "P001")
        self.assertEqual(params["max_depth"], 2)
        self.assertEqual(params["rel_types"], ["CALLED"])
        self.assertEqual(result["center_id"], "P001")
        self.assertEqual(result["counts"]["nodes"], 2)
        self.assertEqual(result["relationships"][0]["provenance"]["source"], "cdr")
        self.assertEqual(
            result["relationships"][0]["provenance"]["source_ref"],
            "cdr:P001:P002:2026-01-01",
        )

    @patch("app.services.neo4j_analytics.run_cypher")
    def test_path_query_returns_shortest_path_payload(self, mock_run_cypher):
        source = _FakeNode(["Person"], {"person_id": "P001"})
        target = _FakeNode(["Person"], {"person_id": "P003"})
        middle = _FakeNode(["Person"], {"person_id": "P002"})
        rel1 = _FakeRelationship(
            "CALLED",
            source,
            middle,
            {"source": "cdr", "source_ref": "cdr:1", "timestamp": "2026-02-01"},
        )
        rel2 = _FakeRelationship(
            "CALLED",
            middle,
            target,
            {"source": "cdr", "source_ref": "cdr:2", "timestamp": "2026-02-02"},
        )

        mock_run_cypher.side_effect = [
            [{"person_id": "P001"}],
            [{"person_id": "P003"}],
            [{"nodes": [source, middle, target], "relationships": [rel1, rel2]}],
        ]

        result = neo4j_analytics.query_person_path(
            "P001",
            "P003",
            max_depth=4,
            relationship_types=["CALLED"],
        )

        path_call = mock_run_cypher.call_args_list[2]
        cypher = path_call.args[0]
        params = path_call.args[1]

        self.assertIn("$source_id", cypher)
        self.assertIn("$target_id", cypher)
        self.assertIn("shortestPath", cypher)
        self.assertEqual(params["source_id"], "P001")
        self.assertEqual(params["target_id"], "P003")
        self.assertTrue(result["found"])
        self.assertEqual(result["counts"]["nodes"], 3)
        self.assertEqual(result["counts"]["relationships"], 2)

    @patch("app.services.neo4j_analytics.run_cypher")
    def test_path_query_returns_not_found_when_no_path(self, mock_run_cypher):
        mock_run_cypher.side_effect = [
            [{"person_id": "P001"}],
            [{"person_id": "P010"}],
            [{"nodes": None, "relationships": None}],
        ]

        result = neo4j_analytics.query_person_path("P001", "P010")

        self.assertFalse(result["found"])
        self.assertEqual(result["counts"]["nodes"], 0)

    @patch("app.services.neo4j_analytics.run_cypher")
    def test_person_not_found_raises(self, mock_run_cypher):
        mock_run_cypher.return_value = []

        with self.assertRaises(neo4j_analytics.PersonNotFoundError):
            neo4j_analytics.query_person_neighborhood("P999")


class Neo4jAnalyticsEndpointTests(unittest.TestCase):
    @patch("app.api.neo4j_analytics.query_person_neighborhood")
    def test_neighborhood_endpoint(self, mock_query):
        from app.api.neo4j_analytics import get_person_neighborhood

        mock_query.return_value = {
            "center_id": "P001",
            "depth": 2,
            "nodes": [],
            "relationships": [],
            "counts": {"nodes": 0, "relationships": 0},
            "filters": {},
        }

        result = get_person_neighborhood(
            person_id="P001",
            depth=2,
            relationship_types="CALLED,OWNS",
            from_datetime="2026-01-01",
            to_datetime="2026-12-31",
        )

        self.assertEqual(result["center_id"], "P001")
        mock_query.assert_called_once_with(
            "P001",
            max_depth=2,
            relationship_types=["CALLED", "OWNS"],
            from_datetime="2026-01-01",
            to_datetime="2026-12-31",
        )

    @patch("app.api.neo4j_analytics.query_person_path")
    def test_path_endpoint(self, mock_query):
        from app.api.neo4j_analytics import get_person_path

        mock_query.return_value = {
            "source_id": "P001",
            "target_id": "P002",
            "found": True,
            "nodes": [],
            "relationships": [],
            "counts": {"nodes": 0, "relationships": 0},
            "filters": {},
        }

        result = get_person_path(
            source_id="P001",
            target_id="P002",
            max_depth=4,
            relationship_types="CALLED",
        )

        self.assertTrue(result["found"])
        mock_query.assert_called_once()
        self.assertEqual(mock_query.call_args.args, ("P001", "P002"))
        self.assertEqual(mock_query.call_args.kwargs["max_depth"], 4)
        self.assertEqual(mock_query.call_args.kwargs["relationship_types"], ["CALLED"])


if __name__ == "__main__":
    unittest.main()
