"""Tests for graph-aware risk integration."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import networkx as nx

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.analytics import (  # noqa: E402
    GRAPH_PROPAGATION_MAX,
    calculate_risk,
)


def _build_test_graph() -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    graph.add_node("P001", entity_type="person", name="Alice")
    graph.add_node("P002", entity_type="person", name="Bob")
    graph.add_edge("P001", "P002", relationship="CALLED")
    return graph


class GraphAwareRiskTests(unittest.TestCase):
    @patch("app.services.analytics.calculate_centrality")
    def test_risk_without_seeds_preserves_existing_payload(self, mock_centrality):
        mock_centrality.return_value = [
            {
                "entity_id": "P001",
                "degree_centrality": 0.5,
                "betweenness_centrality": 0.1,
                "pagerank": 0.2,
            },
            {
                "entity_id": "P002",
                "degree_centrality": 0.5,
                "betweenness_centrality": 0.1,
                "pagerank": 0.2,
            },
        ]

        result = calculate_risk(_build_test_graph())

        self.assertEqual(result[0]["scoring_method"], "rules_v1")
        self.assertNotIn("graph_contribution", result[0])
        self.assertNotIn("personalized_pagerank", result[0])
        self.assertNotIn("graph_propagation", result[0]["signals"])

    @patch("app.services.analytics._load_personalized_pagerank_scores")
    @patch("app.services.analytics.calculate_centrality")
    def test_risk_with_seeds_adds_bounded_graph_contribution(
        self,
        mock_centrality,
        mock_graph_scores,
    ):
        mock_centrality.return_value = [
            {
                "entity_id": "P001",
                "degree_centrality": 0.0,
                "betweenness_centrality": 0.0,
                "pagerank": 0.0,
            },
            {
                "entity_id": "P002",
                "degree_centrality": 0.0,
                "betweenness_centrality": 0.0,
                "pagerank": 0.0,
            },
        ]
        mock_graph_scores.return_value = {
            "P001": 0.95,
            "P002": 0.10,
        }

        results = calculate_risk(_build_test_graph(), graph_seeds=["P001"])
        by_id = {row["entity_id"]: row for row in results}

        self.assertEqual(by_id["P001"]["graph_contribution"], GRAPH_PROPAGATION_MAX)
        self.assertEqual(by_id["P001"]["personalized_pagerank"], 0.95)
        self.assertEqual(by_id["P001"]["signals"]["graph_propagation"], 1.0)
        self.assertEqual(by_id["P001"]["scoring_method"], "rules_v1+graph_propagation")
        self.assertLessEqual(by_id["P001"]["graph_contribution"], GRAPH_PROPAGATION_MAX)
        self.assertLess(by_id["P001"]["graph_contribution"], 50)

    @patch("app.services.analytics._load_personalized_pagerank_scores")
    @patch("app.services.analytics.calculate_centrality")
    def test_graph_contribution_does_not_change_risk_bands_unfairly(
        self,
        mock_centrality,
        mock_graph_scores,
    ):
        mock_centrality.return_value = [
            {
                "entity_id": "P001",
                "degree_centrality": 0.0,
                "betweenness_centrality": 0.0,
                "pagerank": 0.0,
            }
        ]
        mock_graph_scores.return_value = {"P001": 1.0}

        base = calculate_risk(_build_test_graph())
        with_graph = calculate_risk(_build_test_graph(), graph_seeds=["P001"])

        self.assertEqual(with_graph[0]["risk_score"], base[0]["risk_score"] + GRAPH_PROPAGATION_MAX)
        self.assertLessEqual(with_graph[0]["graph_contribution"], GRAPH_PROPAGATION_MAX)

    @patch("app.api.analytics.calculate_risk")
    @patch("app.api.analytics.build_criminal_network")
    def test_risk_endpoint_passes_graph_seeds(self, mock_graph, mock_risk):
        from app.api.analytics import get_risk_scores

        mock_graph.return_value = _build_test_graph()
        mock_risk.return_value = []

        get_risk_scores(graph_seeds="P001,P002")

        mock_risk.assert_called_once()
        self.assertEqual(mock_risk.call_args.kwargs["graph_seeds"], ["P001", "P002"])

    @patch("app.services.neo4j_gds_analytics.calculate_personalized_pagerank")
    def test_risk_continues_when_gds_is_unavailable(self, mock_personalized):
        from app.services.neo4j_gds_analytics import GdsUnavailableError

        mock_personalized.side_effect = GdsUnavailableError(
            "Neo4j Graph Data Science (GDS) is not available on this Aura instance"
        )

        results = calculate_risk(_build_test_graph(), graph_seeds=["P001"])
        by_id = {row["entity_id"]: row for row in results}

        self.assertEqual(len(results), 2)
        self.assertEqual(by_id["P001"]["scoring_method"], "rules_v1+graph_propagation")
        self.assertEqual(by_id["P001"]["graph_contribution"], 0)
        self.assertIsNone(by_id["P001"]["personalized_pagerank"])

    @patch("app.services.neo4j_gds_analytics.calculate_personalized_pagerank")
    def test_in_memory_centrality_does_not_call_gds(self, mock_personalized):
        from app.services.analytics import calculate_centrality

        mock_personalized.side_effect = AssertionError("GDS must remain optional")

        results = calculate_centrality(_build_test_graph())

        self.assertEqual(len(results), 2)
        mock_personalized.assert_not_called()


if __name__ == "__main__":
    unittest.main()
