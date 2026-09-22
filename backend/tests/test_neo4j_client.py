"""Neo4j client and health endpoint tests (no live Aura credentials)."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core import config  # noqa: E402
from app.services import neo4j_client  # noqa: E402


class Neo4jConfigTests(unittest.TestCase):
    def test_neo4j_configured_requires_all_settings(self):
        with patch.object(config, "load_env"):
            with patch.object(config, "NEO4J_URI", "neo4j+s://example.databases.neo4j.io"), patch.object(
                config, "NEO4J_USERNAME", "neo4j"
            ), patch.object(config, "NEO4J_PASSWORD", "secret"):
                self.assertTrue(config.neo4j_configured())

            with patch.object(config, "NEO4J_URI", ""), patch.object(
                config, "NEO4J_USERNAME", "neo4j"
            ), patch.object(config, "NEO4J_PASSWORD", "secret"):
                self.assertFalse(config.neo4j_configured())


class Neo4jClientTests(unittest.TestCase):
    def setUp(self):
        neo4j_client.close_neo4j_driver()

    def tearDown(self):
        neo4j_client.close_neo4j_driver()

    def test_get_driver_returns_none_when_unconfigured(self):
        with patch.object(config, "neo4j_configured", return_value=False):
            self.assertIsNone(neo4j_client.get_neo4j_driver())

    @patch("app.services.neo4j_client.GraphDatabase.driver")
    def test_verify_connectivity_connected(self, mock_driver_factory):
        mock_driver = MagicMock()
        mock_driver_factory.return_value = mock_driver

        with patch.object(config, "neo4j_configured", return_value=True):
            with patch.object(config, "NEO4J_URI", "neo4j+s://example.databases.neo4j.io"):
                with patch.object(config, "NEO4J_USERNAME", "neo4j"):
                    with patch.object(config, "NEO4J_PASSWORD", "secret"):
                        result = neo4j_client.verify_neo4j_connectivity()

        self.assertEqual(result["status"], "connected")
        mock_driver.verify_connectivity.assert_called_once()

    @patch("app.services.neo4j_client.GraphDatabase.driver")
    def test_verify_connectivity_unavailable_on_driver_error(self, mock_driver_factory):
        mock_driver = MagicMock()
        mock_driver.verify_connectivity.side_effect = RuntimeError("connection failed")
        mock_driver_factory.return_value = mock_driver

        with patch.object(config, "neo4j_configured", return_value=True):
            with patch.object(config, "NEO4J_URI", "neo4j+s://example.databases.neo4j.io"):
                with patch.object(config, "NEO4J_USERNAME", "neo4j"):
                    with patch.object(config, "NEO4J_PASSWORD", "secret"):
                        result = neo4j_client.verify_neo4j_connectivity()

        self.assertEqual(result["status"], "unavailable")
        self.assertIn("connection failed", result["detail"])

    def test_verify_connectivity_unavailable_when_unconfigured(self):
        with patch.object(config, "neo4j_configured", return_value=False):
            result = neo4j_client.verify_neo4j_connectivity()

        self.assertEqual(result["status"], "unavailable")
        self.assertIn("not configured", result["detail"])


class Neo4jHealthEndpointTests(unittest.TestCase):
    @patch("app.api.network.verify_neo4j_connectivity")
    def test_neo4j_health_endpoint(self, mock_verify):
        from app.api.network import get_neo4j_health

        mock_verify.return_value = {"status": "connected", "database": "neo4j"}

        result = get_neo4j_health()

        self.assertEqual(result["status"], "connected")
        mock_verify.assert_called_once()


if __name__ == "__main__":
    unittest.main()
