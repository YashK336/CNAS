"""Tests for Neo4j GDS graph analytics."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import neo4j_gds_analytics  # noqa: E402


class Neo4jGdsAnalyticsTests(unittest.TestCase):
    def test_build_native_projection_parameters_use_relationship_type_list(self):
        params = neo4j_gds_analytics.build_native_projection_parameters(
            neo4j_gds_analytics.GRAPH_PROJECTION_NAME,
            "session-123",
        )

        self.assertEqual(params["graph_name"], neo4j_gds_analytics.GRAPH_PROJECTION_NAME)
        self.assertEqual(params["session_id"], "session-123")
        self.assertEqual(
            params["relationship_types"],
            list(neo4j_gds_analytics.PERSON_RELATIONSHIP_TYPES),
        )
        self.assertIsInstance(params["relationship_types"], list)

    def test_build_temporal_projection_parameters_include_window(self):
        params = neo4j_gds_analytics.build_temporal_projection_parameters(
            neo4j_gds_analytics.TEMPORAL_GRAPH_PROJECTION_NAME,
            "session-123",
            from_datetime="2026-01-01",
            to_datetime="2026-06-30",
        )

        self.assertEqual(params["from_datetime"], "2026-01-01")
        self.assertEqual(params["to_datetime"], "2026-06-30")
        self.assertEqual(
            params["relationship_types"],
            list(neo4j_gds_analytics.PERSON_RELATIONSHIP_TYPES),
        )

    def test_parse_projection_stats_handles_aggregation_payload(self):
        stats = neo4j_gds_analytics.parse_projection_stats(
            [
                {
                    "gds.graph.project(...)": {
                        "graphName": neo4j_gds_analytics.TEMPORAL_GRAPH_PROJECTION_NAME,
                        "nodeCount": 50,
                        "relationshipCount": 120,
                        "projectMillis": 8,
                    }
                }
            ],
            graph_name=neo4j_gds_analytics.TEMPORAL_GRAPH_PROJECTION_NAME,
        )

        self.assertEqual(stats["graph_name"], neo4j_gds_analytics.TEMPORAL_GRAPH_PROJECTION_NAME)
        self.assertEqual(stats["node_count"], 50)
        self.assertEqual(stats["relationship_count"], 120)

    @patch("app.services.neo4j_gds_analytics._run_gds")
    def test_ensure_gds_session_uses_configured_settings(self, mock_run_gds):
        mock_run_gds.return_value = [
            {
                "id": "session-123",
                "name": "cnas-analytics",
                "memory": "2GB",
                "status": "Ready",
            }
        ]

        session = neo4j_gds_analytics.ensure_gds_session()

        self.assertEqual(session["session_id"], "session-123")
        self.assertIn("gds.session.getOrCreate", mock_run_gds.call_args.args[0])
        self.assertEqual(mock_run_gds.call_args.args[1]["memory"], "2GB")
        self.assertEqual(mock_run_gds.call_args.args[1]["ttl_minutes"], 30)

    @patch("app.services.neo4j_gds_analytics.ensure_gds_session")
    @patch("app.services.neo4j_gds_analytics._run_gds")
    def test_ensure_projection_drops_existing_graph(self, mock_run_gds, mock_session):
        mock_session.return_value = {
            "session_id": "session-123",
            "session_name": "cnas-analytics",
            "memory": "2GB",
            "status": "Ready",
        }
        mock_run_gds.side_effect = [
            [{"graphName": neo4j_gds_analytics.GRAPH_PROJECTION_NAME}],
            [],
            [{"graphName": neo4j_gds_analytics.GRAPH_PROJECTION_NAME}],
            [
                {
                    "graphName": neo4j_gds_analytics.GRAPH_PROJECTION_NAME,
                    "nodeCount": 50,
                    "relationshipCount": 5000,
                    "projectMillis": 12,
                }
            ],
        ]

        stats = neo4j_gds_analytics.ensure_person_graph_projection()

        self.assertEqual(stats["node_count"], 50)
        self.assertEqual(stats["session"]["session_id"], "session-123")
        self.assertEqual(mock_run_gds.call_count, 4)
        self.assertIn("gds.graph.drop", mock_run_gds.call_args_list[0].args[0])
        self.assertIn("gds.graph.drop", mock_run_gds.call_args_list[1].args[0])
        project_call = mock_run_gds.call_args_list[3]
        self.assertIn("gds.graph.project", project_call.args[0])
        self.assertEqual(
            project_call.args[1]["relationship_types"],
            list(neo4j_gds_analytics.PERSON_RELATIONSHIP_TYPES),
        )
        self.assertEqual(project_call.args[1]["session_id"], "session-123")

    @patch("app.services.neo4j_gds_analytics._run_gds")
    def test_drop_graph_projection_is_safe_when_missing(self, mock_run_gds):
        mock_run_gds.return_value = []

        dropped = neo4j_gds_analytics.drop_graph_projection("missing-graph")

        self.assertFalse(dropped)
        self.assertIn("gds.graph.drop", mock_run_gds.call_args.args[0])
        self.assertEqual(mock_run_gds.call_args.args[1]["graph_name"], "missing-graph")

    @patch("app.services.neo4j_gds_analytics._run_gds")
    def test_drop_graph_projection_removes_existing_graph(self, mock_run_gds):
        mock_run_gds.return_value = [{"graphName": neo4j_gds_analytics.GRAPH_PROJECTION_NAME}]

        dropped = neo4j_gds_analytics.drop_graph_projection(
            neo4j_gds_analytics.GRAPH_PROJECTION_NAME
        )

        self.assertTrue(dropped)

    @patch("app.services.neo4j_gds_analytics._run_gds")
    def test_drop_all_cnas_graph_projections_cleans_both_names(self, mock_run_gds):
        mock_run_gds.return_value = []

        neo4j_gds_analytics.drop_all_cnas_graph_projections()

        self.assertEqual(mock_run_gds.call_count, 2)
        dropped_names = [call.args[1]["graph_name"] for call in mock_run_gds.call_args_list]
        self.assertEqual(
            dropped_names,
            list(neo4j_gds_analytics.CNAS_GRAPH_PROJECTION_NAMES),
        )

    @patch("app.services.neo4j_gds_analytics.ensure_gds_session")
    @patch("app.services.neo4j_gds_analytics._run_gds")
    def test_first_projection_creation(self, mock_run_gds, mock_session):
        mock_session.return_value = {"session_id": "session-123", "session_name": "cnas-analytics"}
        mock_run_gds.side_effect = [
            [],
            [],
            [],
            [{"graphName": neo4j_gds_analytics.GRAPH_PROJECTION_NAME, "nodeCount": 3, "relationshipCount": 4, "projectMillis": 1}],
        ]

        stats = neo4j_gds_analytics.ensure_person_graph_projection()

        self.assertEqual(stats["graph_name"], neo4j_gds_analytics.GRAPH_PROJECTION_NAME)
        self.assertEqual(stats["node_count"], 3)

    @patch("app.services.neo4j_gds_analytics.ensure_gds_session")
    @patch("app.services.neo4j_gds_analytics._run_gds")
    def test_repeated_projection_creation_is_idempotent(self, mock_run_gds, mock_session):
        mock_session.return_value = {"session_id": "session-123", "session_name": "cnas-analytics"}
        mock_run_gds.side_effect = [
            [{"graphName": neo4j_gds_analytics.GRAPH_PROJECTION_NAME}],
            [],
            [{"graphName": neo4j_gds_analytics.GRAPH_PROJECTION_NAME}],
            [{"graphName": neo4j_gds_analytics.GRAPH_PROJECTION_NAME, "nodeCount": 3, "relationshipCount": 4, "projectMillis": 1}],
            [{"graphName": neo4j_gds_analytics.GRAPH_PROJECTION_NAME}],
            [],
            [{"graphName": neo4j_gds_analytics.GRAPH_PROJECTION_NAME}],
            [{"graphName": neo4j_gds_analytics.GRAPH_PROJECTION_NAME, "nodeCount": 3, "relationshipCount": 4, "projectMillis": 2}],
        ]

        first = neo4j_gds_analytics.ensure_person_graph_projection()
        second = neo4j_gds_analytics.ensure_person_graph_projection()

        self.assertEqual(first["graph_name"], second["graph_name"])
        self.assertEqual(mock_run_gds.call_count, 8)

    @patch("app.services.neo4j_gds_analytics.ensure_gds_session")
    @patch("app.services.neo4j_gds_analytics._run_gds")
    def test_projection_retries_after_graph_already_exists(self, mock_run_gds, mock_session):
        mock_session.return_value = {"session_id": "session-123", "session_name": "cnas-analytics"}
        mock_run_gds.side_effect = [
            [],
            [],
            [],
            neo4j_gds_analytics.GdsUnavailableError(
                "GraphAlreadyExistsException: A graph with name 'cnas-person-analytics' already exists"
            ),
            [{"graphName": neo4j_gds_analytics.GRAPH_PROJECTION_NAME}],
            [{"graphName": neo4j_gds_analytics.GRAPH_PROJECTION_NAME, "nodeCount": 3, "relationshipCount": 4, "projectMillis": 3}],
        ]

        stats = neo4j_gds_analytics.ensure_person_graph_projection()

        self.assertEqual(stats["node_count"], 3)
        self.assertEqual(mock_run_gds.call_count, 6)

    @patch("app.services.neo4j_gds_analytics._ensure_person_graph_projection_unlocked")
    @patch("app.services.neo4j_gds_analytics._run_gds")
    def test_pagerank_after_repeated_refresh(self, mock_run_gds, mock_projection):
        mock_projection.side_effect = [
            {
                "graph_name": neo4j_gds_analytics.GRAPH_PROJECTION_NAME,
                "node_count": 3,
                "relationship_count": 4,
                "project_millis": 1,
            },
            {
                "graph_name": neo4j_gds_analytics.GRAPH_PROJECTION_NAME,
                "node_count": 3,
                "relationship_count": 4,
                "project_millis": 2,
            },
        ]
        mock_run_gds.return_value = [
            {"entity_id": "P001", "name": "Alice", "pagerank": 0.5},
        ]

        first = neo4j_gds_analytics.calculate_person_pagerank(refresh_projection=True)
        second = neo4j_gds_analytics.calculate_person_pagerank(refresh_projection=True)

        self.assertEqual(first["total"], 1)
        self.assertEqual(second["total"], 1)
        self.assertEqual(mock_projection.call_count, 2)

    @patch("app.services.neo4j_gds_analytics._ensure_person_graph_projection_unlocked")
    @patch("app.services.neo4j_gds_analytics._run_gds")
    def test_louvain_after_repeated_refresh(self, mock_run_gds, mock_projection):
        mock_projection.side_effect = [
            {
                "graph_name": neo4j_gds_analytics.GRAPH_PROJECTION_NAME,
                "node_count": 3,
                "relationship_count": 4,
                "project_millis": 1,
            },
            {
                "graph_name": neo4j_gds_analytics.GRAPH_PROJECTION_NAME,
                "node_count": 3,
                "relationship_count": 4,
                "project_millis": 2,
            },
        ]
        mock_run_gds.return_value = [
            {"entity_id": "P001", "name": "Alice", "communityId": 1},
        ]

        first = neo4j_gds_analytics.detect_person_communities(refresh_projection=True)
        second = neo4j_gds_analytics.detect_person_communities(refresh_projection=True)

        self.assertEqual(first["total_communities"], 1)
        self.assertEqual(second["total_communities"], 1)
        self.assertEqual(mock_projection.call_count, 2)

    @patch("app.services.neo4j_gds_analytics.ensure_gds_session")
    @patch("app.services.neo4j_gds_analytics._run_gds")
    def test_temporal_projection_uses_aura_cypher_projection(self, mock_run_gds, mock_session):
        mock_session.return_value = {
            "session_id": "session-123",
            "session_name": "cnas-analytics",
            "memory": "2GB",
            "status": "Ready",
        }
        mock_run_gds.side_effect = [
            [],
            [],
            [],
            [
                {
                    "gds.graph.project(...)": {
                        "graphName": neo4j_gds_analytics.TEMPORAL_GRAPH_PROJECTION_NAME,
                        "nodeCount": 50,
                        "relationshipCount": 120,
                        "projectMillis": 8,
                    }
                }
            ],
        ]

        stats = neo4j_gds_analytics.ensure_person_graph_projection(
            from_datetime="2026-01-01",
            to_datetime="2026-06-30",
        )

        self.assertEqual(stats["graph_name"], neo4j_gds_analytics.TEMPORAL_GRAPH_PROJECTION_NAME)
        temporal_call = mock_run_gds.call_args_list[3]
        self.assertIn("CYPHER runtime=parallel", temporal_call.args[0])
        self.assertIn("RETURN gds.graph.project", temporal_call.args[0])
        self.assertEqual(temporal_call.args[1]["from_datetime"], "2026-01-01")
        self.assertEqual(temporal_call.args[1]["to_datetime"], "2026-06-30")
        self.assertEqual(temporal_call.args[1]["session_id"], "session-123")

    @patch("app.services.neo4j_gds_analytics._ensure_person_graph_projection_unlocked")
    @patch("app.services.neo4j_gds_analytics._run_gds")
    def test_pagerank_returns_frontend_friendly_payload(self, mock_run_gds, mock_projection):
        mock_projection.return_value = {
            "graph_name": neo4j_gds_analytics.GRAPH_PROJECTION_NAME,
            "node_count": 3,
            "relationship_count": 4,
            "project_millis": 5,
        }
        mock_run_gds.return_value = [
            {"entity_id": "P001", "name": "Alice", "pagerank": 0.5123},
            {"entity_id": "P002", "name": "Bob", "pagerank": 0.2877},
        ]

        result = neo4j_gds_analytics.calculate_person_pagerank()

        self.assertEqual(result["method"], "gds.pageRank")
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["data"][0]["entity_id"], "P001")
        self.assertEqual(result["data"][0]["rank"], 1)
        self.assertEqual(result["data"][0]["pagerank"], 0.5123)
        self.assertFalse(result["time_window"]["applied"])
        mock_run_gds.assert_called_once()
        self.assertIn("$graph_name", mock_run_gds.call_args.args[0])

    @patch("app.services.neo4j_gds_analytics._ensure_person_graph_projection_unlocked")
    @patch("app.services.neo4j_gds_analytics._run_gds")
    def test_louvain_groups_communities(self, mock_run_gds, mock_projection):
        mock_projection.return_value = {
            "graph_name": neo4j_gds_analytics.GRAPH_PROJECTION_NAME,
            "node_count": 3,
            "relationship_count": 4,
            "project_millis": 5,
        }
        mock_run_gds.return_value = [
            {"entity_id": "P001", "name": "Alice", "communityId": 1},
            {"entity_id": "P002", "name": "Bob", "communityId": 1},
            {"entity_id": "P003", "name": "Carol", "communityId": 2},
        ]

        result = neo4j_gds_analytics.detect_person_communities()

        self.assertEqual(result["method"], "gds.louvain")
        self.assertEqual(result["total_communities"], 2)
        self.assertEqual(result["communities"][0]["size"], 2)
        self.assertEqual(result["communities"][0]["members"][0]["entity_id"], "P001")
        self.assertEqual(result["communities"][0]["display_id"], 1)

    @patch("app.services.neo4j_gds_analytics.run_cypher")
    def test_gds_unavailable_error_is_raised(self, mock_run_cypher):
        mock_run_cypher.side_effect = Exception("Unknown function 'gds.graph.exists'")

        with self.assertRaises(neo4j_gds_analytics.GdsUnavailableError):
            neo4j_gds_analytics.ensure_person_graph_projection()

    @patch("app.services.neo4j_gds_analytics.run_cypher")
    def test_run_gds_maps_aura_procedure_errors(self, mock_run_cypher):
        mock_run_cypher.side_effect = Exception(
            "There is no procedure with the name `gds.session.getOrCreate`."
        )

        with self.assertRaises(neo4j_gds_analytics.GdsUnavailableError):
            neo4j_gds_analytics._run_gds("CALL gds.session.getOrCreate()")

    @patch("app.services.neo4j_gds_analytics.run_cypher")
    def test_run_gds_reraises_neo4j_unavailable_without_wrapping(self, mock_run_cypher):
        from app.services.neo4j_analytics import Neo4jUnavailableError

        mock_run_cypher.side_effect = Neo4jUnavailableError(
            "Neo4j environment variables are not configured"
        )

        with self.assertRaises(Neo4jUnavailableError) as ctx:
            neo4j_gds_analytics._run_gds("RETURN 1")

        self.assertIs(type(ctx.exception), Neo4jUnavailableError)


class Neo4jGdsEndpointTests(unittest.TestCase):
    @patch("app.api.neo4j_analytics.calculate_person_pagerank")
    def test_pagerank_endpoint(self, mock_pagerank):
        from app.api.neo4j_analytics import get_neo4j_pagerank

        mock_pagerank.return_value = {
            "total": 1,
            "method": "gds.pageRank",
            "graph_projection": neo4j_gds_analytics.GRAPH_PROJECTION_NAME,
            "projection_stats": {},
            "data": [{"entity_id": "P001", "name": "Alice", "pagerank": 0.5, "rank": 1}],
        }

        result = get_neo4j_pagerank(refresh_projection=True)

        self.assertEqual(result["total"], 1)
        mock_pagerank.assert_called_once()
        self.assertEqual(mock_pagerank.call_args.kwargs["refresh_projection"], True)
        self.assertIn("from_datetime", mock_pagerank.call_args.kwargs)
        self.assertIn("to_datetime", mock_pagerank.call_args.kwargs)

    @patch("app.api.neo4j_analytics.detect_person_communities")
    def test_communities_endpoint(self, mock_communities):
        from app.api.neo4j_analytics import get_neo4j_communities

        mock_communities.return_value = {
            "total_communities": 1,
            "method": "gds.louvain",
            "graph_projection": neo4j_gds_analytics.GRAPH_PROJECTION_NAME,
            "projection_stats": {},
            "communities": [],
        }

        result = get_neo4j_communities(refresh_projection=True)

        self.assertEqual(result["total_communities"], 1)
        mock_communities.assert_called_once()
        self.assertEqual(mock_communities.call_args.kwargs["refresh_projection"], True)
        self.assertIn("from_datetime", mock_communities.call_args.kwargs)
        self.assertIn("to_datetime", mock_communities.call_args.kwargs)

    @patch("app.api.neo4j_analytics.calculate_person_pagerank")
    def test_pagerank_endpoint_returns_503_when_gds_unavailable(self, mock_pagerank):
        from fastapi import HTTPException

        from app.api.neo4j_analytics import get_neo4j_pagerank

        mock_pagerank.side_effect = neo4j_gds_analytics.GdsUnavailableError(
            "Neo4j Graph Data Science (GDS) is not available on this Aura instance"
        )

        with self.assertRaises(HTTPException) as ctx:
            get_neo4j_pagerank(refresh_projection=True)

        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("GDS", str(ctx.exception.detail))

    @patch("app.api.neo4j_analytics.detect_person_communities")
    def test_communities_endpoint_returns_503_when_gds_unavailable(self, mock_communities):
        from fastapi import HTTPException

        from app.api.neo4j_analytics import get_neo4j_communities

        mock_communities.side_effect = neo4j_gds_analytics.GdsUnavailableError(
            "Neo4j Graph Data Science (GDS) is not available on this Aura instance"
        )

        with self.assertRaises(HTTPException) as ctx:
            get_neo4j_communities(refresh_projection=True)

        self.assertEqual(ctx.exception.status_code, 503)

    @patch("app.api.neo4j_analytics.calculate_personalized_pagerank")
    def test_personalized_pagerank_endpoint_returns_503_when_gds_unavailable(
        self,
        mock_personalized,
    ):
        from fastapi import HTTPException

        from app.api.neo4j_analytics import get_neo4j_personalized_pagerank

        mock_personalized.side_effect = neo4j_gds_analytics.GdsUnavailableError(
            "Neo4j Graph Data Science (GDS) is not available on this Aura instance"
        )

        with self.assertRaises(HTTPException) as ctx:
            get_neo4j_personalized_pagerank(seeds="P001", refresh_projection=True)

        self.assertEqual(ctx.exception.status_code, 503)


class Neo4jPersonalizedPageRankTests(unittest.TestCase):
    @patch("app.services.neo4j_gds_analytics._ensure_person_graph_projection_unlocked")
    @patch("app.services.neo4j_gds_analytics._run_gds")
    def test_personalized_pagerank_returns_ranked_payload(self, mock_run_gds, mock_projection):
        mock_projection.return_value = {
            "graph_name": neo4j_gds_analytics.GRAPH_PROJECTION_NAME,
            "node_count": 3,
            "relationship_count": 4,
            "project_millis": 5,
        }
        mock_run_gds.side_effect = [
            [{"source_node_ids": [1], "matched_seed_ids": ["P001"]}],
            [
                {"entity_id": "P001", "name": "Alice", "personalized_pagerank": 0.61},
                {"entity_id": "P002", "name": "Bob", "personalized_pagerank": 0.39},
            ],
        ]

        result = neo4j_gds_analytics.calculate_personalized_pagerank(["P001"])

        self.assertEqual(result["method"], "gds.pageRank.personalized")
        self.assertEqual(result["seeds"], ["P001"])
        self.assertEqual(result["data"][0]["personalized_pagerank"], 0.61)
        self.assertEqual(result["data"][0]["rank"], 1)
        self.assertIn("sourceNodes", mock_run_gds.call_args_list[1].args[0])

    def test_personalized_pagerank_requires_seeds(self):
        with self.assertRaises(ValueError):
            neo4j_gds_analytics.calculate_personalized_pagerank([])

    @patch("app.api.neo4j_analytics.calculate_personalized_pagerank")
    def test_personalized_pagerank_endpoint(self, mock_personalized):
        from app.api.neo4j_analytics import get_neo4j_personalized_pagerank

        mock_personalized.return_value = {
            "total": 1,
            "method": "gds.pageRank.personalized",
            "seeds": ["P001", "P002"],
            "graph_projection": neo4j_gds_analytics.GRAPH_PROJECTION_NAME,
            "projection_stats": {},
            "data": [
                {
                    "entity_id": "P001",
                    "name": "Alice",
                    "personalized_pagerank": 0.5,
                    "rank": 1,
                }
            ],
        }

        result = get_neo4j_personalized_pagerank(seeds="P001,P002", refresh_projection=True)

        self.assertEqual(result["seeds"], ["P001", "P002"])
        mock_personalized.assert_called_once_with(["P001", "P002"], refresh_projection=True)


class Neo4jTemporalGdsAnalyticsTests(unittest.TestCase):
    def test_invalid_temporal_range_raises(self):
        with self.assertRaises(ValueError):
            neo4j_gds_analytics.normalize_temporal_window(
                "2026-12-31",
                "2026-01-01",
            )

    def test_time_window_payload_without_filters(self):
        payload = neo4j_gds_analytics.time_window_payload()
        self.assertFalse(payload["applied"])
        self.assertIsNone(payload["from_datetime"])

    @patch("app.services.neo4j_gds_analytics._ensure_person_graph_projection_unlocked")
    @patch("app.services.neo4j_gds_analytics._run_gds")
    def test_pagerank_applies_temporal_projection(self, mock_run_gds, mock_projection):
        mock_projection.return_value = {
            "graph_name": neo4j_gds_analytics.TEMPORAL_GRAPH_PROJECTION_NAME,
            "node_count": 50,
            "relationship_count": 120,
            "project_millis": 8,
            "time_window": {
                "applied": True,
                "from_datetime": "2026-01-01",
                "to_datetime": "2026-06-30",
            },
        }
        mock_run_gds.return_value = [
            {"entity_id": "P001", "name": "Alice", "pagerank": 0.4},
        ]

        result = neo4j_gds_analytics.calculate_person_pagerank(
            from_datetime="2026-01-01",
            to_datetime="2026-06-30",
        )

        self.assertTrue(result["time_window"]["applied"])
        self.assertEqual(result["time_window"]["from_datetime"], "2026-01-01")
        self.assertEqual(result["time_window"]["to_datetime"], "2026-06-30")
        mock_projection.assert_called_once_with(
            from_datetime="2026-01-01",
            to_datetime="2026-06-30",
        )
        self.assertEqual(
            mock_run_gds.call_args.args[1]["graph_name"],
            neo4j_gds_analytics.TEMPORAL_GRAPH_PROJECTION_NAME,
        )

    def test_boundary_equal_datetimes_are_valid(self):
        window = neo4j_gds_analytics.normalize_temporal_window(
            "2026-06-01",
            "2026-06-01",
        )
        self.assertEqual(window["from_datetime"], window["to_datetime"])

    @patch("app.services.neo4j_gds_analytics._ensure_person_graph_projection_unlocked")
    @patch("app.services.neo4j_gds_analytics._run_gds")
    def test_empty_temporal_window_returns_no_results(self, mock_run_gds, mock_projection):
        mock_projection.return_value = {
            "graph_name": neo4j_gds_analytics.TEMPORAL_GRAPH_PROJECTION_NAME,
            "node_count": 50,
            "relationship_count": 0,
            "project_millis": 3,
            "time_window": {
                "applied": True,
                "from_datetime": "2030-01-01",
                "to_datetime": "2030-01-02",
            },
        }

        result = neo4j_gds_analytics.calculate_person_pagerank(
            from_datetime="2030-01-01",
            to_datetime="2030-01-02",
        )

        self.assertEqual(result["total"], 0)
        self.assertEqual(result["data"], [])
        mock_run_gds.assert_not_called()

    @patch("app.services.neo4j_gds_analytics._ensure_person_graph_projection_unlocked")
    @patch("app.services.neo4j_gds_analytics._run_gds")
    def test_communities_include_time_window(self, mock_run_gds, mock_projection):
        mock_projection.return_value = {
            "graph_name": neo4j_gds_analytics.TEMPORAL_GRAPH_PROJECTION_NAME,
            "node_count": 3,
            "relationship_count": 2,
            "project_millis": 4,
            "time_window": {
                "applied": True,
                "from_datetime": "2026-02-01",
                "to_datetime": "2026-02-28",
            },
        }
        mock_run_gds.return_value = [
            {"entity_id": "P001", "name": "Alice", "communityId": 1},
        ]

        result = neo4j_gds_analytics.detect_person_communities(
            from_datetime="2026-02-01",
            to_datetime="2026-02-28",
        )

        self.assertTrue(result["time_window"]["applied"])
        self.assertEqual(result["total_communities"], 1)

    @patch("app.api.neo4j_analytics.calculate_person_pagerank")
    def test_pagerank_endpoint_passes_temporal_filters(self, mock_pagerank):
        from app.api.neo4j_analytics import get_neo4j_pagerank

        mock_pagerank.return_value = {
            "total": 0,
            "method": "gds.pageRank",
            "graph_projection": neo4j_gds_analytics.TEMPORAL_GRAPH_PROJECTION_NAME,
            "projection_stats": {},
            "time_window": {"applied": True, "from_datetime": "2026-01-01", "to_datetime": "2026-03-01"},
            "data": [],
        }

        get_neo4j_pagerank(
            refresh_projection=True,
            from_datetime="2026-01-01",
            to_datetime="2026-03-01",
        )

        mock_pagerank.assert_called_once_with(
            refresh_projection=True,
            from_datetime="2026-01-01",
            to_datetime="2026-03-01",
        )


if __name__ == "__main__":
    unittest.main()
