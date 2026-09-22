"""Tests for local environment loading via python-dotenv."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core import config  # noqa: E402


class ConfigEnvLoadingTests(unittest.TestCase):
    def test_env_file_resolves_to_backend_root(self):
        expected = Path(config.__file__).resolve().parents[2] / ".env"
        self.assertEqual(config.ENV_FILE, expected)

    def test_load_env_reads_dotenv_file(self):
        env_content = (
            "NEO4J_URI=neo4j+s://test.example.databases.neo4j.io\n"
            "NEO4J_USERNAME=neo4j\n"
            "NEO4J_PASSWORD=fake-test-password\n"
            "NEO4J_DATABASE=neo4j\n"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text(env_content, encoding="utf-8")

            with patch.object(config, "ENV_FILE", env_file):
                with patch.dict(os.environ, {}, clear=True):
                    config.load_env()

                    self.assertEqual(
                        os.getenv("NEO4J_URI"),
                        "neo4j+s://test.example.databases.neo4j.io",
                    )
                    self.assertEqual(os.getenv("NEO4J_USERNAME"), "neo4j")
                    self.assertEqual(os.getenv("NEO4J_PASSWORD"), "fake-test-password")
                    self.assertEqual(os.getenv("NEO4J_DATABASE"), "neo4j")
                    self.assertTrue(config.neo4j_configured())

    def test_load_env_refreshes_module_settings(self):
        env_content = (
            "NEO4J_URI=neo4j+s://refresh.example.databases.neo4j.io\n"
            "NEO4J_USERNAME=neo4j\n"
            "NEO4J_PASSWORD=fake-test-password\n"
            "NEO4J_DATABASE=neo4j\n"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text(env_content, encoding="utf-8")

            with patch.object(config, "ENV_FILE", env_file):
                with patch.dict(os.environ, {}, clear=True):
                    config.load_env()

                    self.assertEqual(
                        config.NEO4J_URI,
                        "neo4j+s://refresh.example.databases.neo4j.io",
                    )
                    self.assertEqual(config.NEO4J_USERNAME, "neo4j")
                    self.assertTrue(config.NEO4J_PASSWORD)
                    self.assertTrue(config.neo4j_configured())

    def test_load_env_does_not_override_existing_environment(self):
        env_content = "NEO4J_URI=neo4j+s://from-file.example.databases.neo4j.io\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text(env_content, encoding="utf-8")

            with patch.object(config, "ENV_FILE", env_file):
                with patch.dict(
                    os.environ,
                    {"NEO4J_URI": "neo4j+s://from-shell.example.databases.neo4j.io"},
                    clear=True,
                ):
                    config.load_env()

                    self.assertEqual(
                        os.getenv("NEO4J_URI"),
                        "neo4j+s://from-shell.example.databases.neo4j.io",
                    )


if __name__ == "__main__":
    unittest.main()
