"""Tests for CNAS Neo4j graph ontology mapping and import logic."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.graph.importer import (  # noqa: E402
    _run_batch,
    batch_merge_node_cypher,
    batch_merge_relationship_cypher,
    constraint_cypher,
    import_cnas_graph,
    merge_nodes_in_batches,
    merge_relationships_in_batches,
    merge_node_cypher,
    merge_relationship_cypher,
)
from app.services.graph.mapper import (  # noqa: E402
    GraphPlan,
    NodeSpec,
    RelationshipSpec,
    build_cnas_graph_plan,
    map_structured_import_records,
    provenance,
)
from app.services.graph.ontology import (  # noqa: E402
    LABEL_FIR,
    LABEL_LOCATION,
    LABEL_PERSON,
    REL_CALLED,
    REL_HAS_PHONE,
    REL_INVOLVED_IN,
    REL_TRANSFERRED_MONEY_TO,
    UNIQUE_CONSTRAINTS,
)
from app.services.ingestion import load_source_records  # noqa: E402


def unique_constraint_collisions(plan: GraphPlan) -> list[tuple]:
    """Return unique-constraint collisions the Neo4j importer would hit."""
    owners: dict[tuple[str, str, str], tuple[str, str, str]] = {}
    collisions: list[tuple] = []
    for node in plan.nodes:
        identity = (node.label, node.key_property, str(node.key_value))
        for label, prop in UNIQUE_CONSTRAINTS:
            if node.label != label:
                continue
            value = (
                node.key_value
                if node.key_property == prop
                else node.properties.get(prop)
            )
            if value is None:
                continue
            key = (label, prop, str(value))
            owner = owners.get(key)
            if owner is not None and owner != identity:
                collisions.append((key, owner, identity))
            else:
                owners[key] = identity
    return collisions


class _session_context:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        return False


class GraphOntologyTests(unittest.TestCase):
    def test_unique_constraints_cover_all_primary_labels(self):
        labels = {label for label, _ in UNIQUE_CONSTRAINTS}
        self.assertIn(LABEL_PERSON, labels)
        self.assertIn(LABEL_FIR, labels)
        self.assertEqual(len(UNIQUE_CONSTRAINTS), 9)

    def test_merge_cypher_is_idempotent(self):
        node = NodeSpec(label="Person", key_property="person_id", key_value="P001", properties={"name": "Test"})
        rel = RelationshipSpec(
            rel_type=REL_CALLED,
            from_label="Person",
            from_key="person_id",
            from_value="P001",
            to_label="Person",
            to_key="person_id",
            to_value="P002",
            record_id="cdr:P001:P002:2026-01-01",
            properties={"source": "cdr"},
        )

        self.assertIn("MERGE", merge_node_cypher(node))
        self.assertIn("MERGE", merge_relationship_cypher(rel))
        self.assertIn("record_id", merge_relationship_cypher(rel))
        self.assertIn("IF NOT EXISTS", constraint_cypher("Person", "person_id"))


class GraphMapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = build_cnas_graph_plan()

    def test_plan_includes_core_node_labels(self):
        labels = {node.label for node in self.plan.nodes}
        expected = {
            "Person",
            "Phone",
            "Vehicle",
            "BankAccount",
            "SocialAccount",
            "Location",
            "FIR",
            "Crime",
            "SurveillanceEvent",
        }
        self.assertTrue(expected.issubset(labels))

    def test_plan_includes_core_relationship_types(self):
        rel_types = {rel.rel_type for rel in self.plan.relationships}
        expected = {
            REL_HAS_PHONE,
            REL_CALLED,
            REL_TRANSFERRED_MONEY_TO,
            REL_INVOLVED_IN,
            "SOCIAL_REPLY",
            "SOCIAL_RETWEET",
            "SOCIAL_MENTION",
            "OBSERVED_AT",
            "PRESENT_AT",
            "AT_LOCATION",
            "FOR_CRIME",
        }
        self.assertTrue(expected.issubset(rel_types))

    def test_relationships_include_provenance(self):
        rel = next(rel for rel in self.plan.relationships if rel.rel_type == REL_CALLED)
        self.assertEqual(rel.properties["source"], "cdr")
        self.assertTrue(rel.properties["content_hash"])
        self.assertTrue(rel.properties["ingested_at"])
        self.assertTrue(rel.properties["source_ref"])

    def test_person_nodes_use_canonical_person_ids(self):
        person_ids = {
            node.key_value
            for node in self.plan.nodes
            if node.label == LABEL_PERSON
        }
        self.assertIn("P001", person_ids)
        self.assertTrue(all(person_id.startswith("P") for person_id in person_ids))

    def test_plan_counts_match_dataset_scale(self):
        summary = self.plan.summary()
        self.assertGreaterEqual(summary["node_counts"]["Person"], 50)
        self.assertGreaterEqual(summary["relationship_counts"][REL_CALLED], 3500)
        self.assertGreaterEqual(summary["relationship_counts"][REL_TRANSFERRED_MONEY_TO], 900)
        self.assertGreaterEqual(summary["relationship_counts"][REL_INVOLVED_IN], 40)

    def test_provenance_helper_uses_record_metadata(self):
        record = load_source_records("persons")[0]
        props = provenance(record)
        self.assertEqual(props["source"], "persons")
        self.assertEqual(props["source_ref"], record["record_id"])
        self.assertEqual(props["content_hash"], record["content_hash"])

    def test_location_nodes_use_the_unique_name_merge_key(self):
        location_nodes = [
            node for node in self.plan.nodes if node.label == LABEL_LOCATION
        ]
        self.assertTrue(location_nodes)
        self.assertEqual(
            {node.key_property for node in location_nodes},
            {"name"},
        )
        self.assertFalse(unique_constraint_collisions(self.plan))

    def test_legacy_and_canonical_location_share_one_merge_identity(self):
        colliding = GraphPlan(
            nodes=[
                NodeSpec(
                    label=LABEL_LOCATION,
                    key_property="name",
                    key_value="Mumbai",
                    properties={"source": "fir"},
                ),
                NodeSpec(
                    label=LABEL_LOCATION,
                    key_property="location_id",
                    key_value="Mumbai",
                    properties={"name": "Mumbai"},
                ),
            ]
        )
        self.assertTrue(unique_constraint_collisions(colliding))
        self.assertFalse(unique_constraint_collisions(self.plan))

    def test_structured_import_plan_uses_the_same_location_key(self):
        now = "2026-01-01T00:00:00+00:00"
        plan = map_structured_import_records(
            persons=[
                {
                    "record_id": "import:person",
                    "source": "persons",
                    "content_hash": "a",
                    "ingested_at": now,
                    "data": {
                        "person_id": "P-IMPORT-1",
                        "name": "Import Person",
                        "jurisdiction": "DEL",
                    },
                }
            ],
            firs=[
                {
                    "record_id": "import:fir",
                    "source": "fir",
                    "content_hash": "b",
                    "ingested_at": now,
                    "data": {
                        "fir_id": "FIR-IMPORT-1",
                        "person_id": "P-IMPORT-1",
                        "crime": "Theft",
                        "location": "Mumbai",
                        "jurisdiction": "DEL",
                    },
                }
            ],
        )
        location_nodes = [
            node for node in plan.nodes if node.label == LABEL_LOCATION
        ]
        self.assertEqual(len(location_nodes), 1)
        self.assertEqual(location_nodes[0].key_property, "name")
        self.assertEqual(location_nodes[0].key_value, "Mumbai")
        self.assertEqual(location_nodes[0].properties.get("location_id"), "Mumbai")
        self.assertFalse(unique_constraint_collisions(plan))


class GraphImporterTests(unittest.TestCase):
    def test_batch_queries_use_unwind_and_bounded_transactions(self):
        session = MagicMock()
        node_specs = [
            NodeSpec(label="Person", key_property="person_id", key_value=f"P00{i}", properties={"source": "persons"})
            for i in range(3)
        ]
        relationship_specs = [
            RelationshipSpec(
                rel_type=REL_CALLED,
                from_label="Person",
                from_key="person_id",
                from_value=f"P00{i}",
                to_label="Person",
                to_key="person_id",
                to_value=f"P00{i + 1}",
                record_id=f"record-{i}",
                properties={"source": "cdr"},
            )
            for i in range(2)
        ]

        self.assertEqual(merge_nodes_in_batches(session, node_specs, batch_size=2), 3)
        self.assertEqual(merge_relationships_in_batches(session, relationship_specs, batch_size=2), 2)

        self.assertEqual(session.begin_transaction.call_count, 3)
        transactions = session.begin_transaction.return_value
        self.assertEqual(transactions.run.call_count, 3)
        queries = [call.args[0] for call in transactions.run.call_args_list]
        self.assertTrue(all("UNWIND $rows AS row" in query for query in queries))
        self.assertIn("MERGE (n:Person {person_id: row.key_value})", batch_merge_node_cypher(node_specs[0]))
        self.assertIn("record_id: row.record_id", batch_merge_relationship_cypher(relationship_specs[0]))
        self.assertTrue(all(call.kwargs["rows"] for call in transactions.run.call_args_list))

    def test_batch_transaction_rolls_back_when_write_fails(self):
        transaction = MagicMock()
        transaction.run.side_effect = RuntimeError("write failed")
        session = MagicMock()
        session.begin_transaction.return_value = transaction

        with self.assertRaisesRegex(RuntimeError, "write failed"):
            _run_batch(session, "UNWIND $rows AS row RETURN row", [{"value": 1}])

        transaction.rollback.assert_called_once_with()
        transaction.commit.assert_not_called()

    def test_dry_run_returns_plan_summary_without_driver(self):
        with patch("app.services.graph.importer.get_neo4j_driver") as mock_driver:
            result = import_cnas_graph(dry_run=True)

        mock_driver.assert_not_called()
        self.assertEqual(result["status"], "dry_run")
        self.assertGreater(result["nodes"], 0)
        self.assertGreater(result["relationships"], 0)

    def test_import_executes_merge_operations_via_session(self):
        mock_session = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_session
        mock_context.__exit__.return_value = False

        plan = GraphPlan(
            nodes=[NodeSpec(label="Person", key_property="person_id", key_value="P001")],
            relationships=[
                RelationshipSpec(
                    rel_type=REL_CALLED,
                    from_label="Person",
                    from_key="person_id",
                    from_value="P001",
                    to_label="Person",
                    to_key="person_id",
                    to_value="P002",
                    record_id="test-record",
                    properties={"source": "cdr"},
                )
            ],
        )

        with patch("app.services.graph.importer.get_neo4j_driver") as mock_driver:
            mock_driver.return_value.session.return_value = mock_context
            result = import_cnas_graph(plan=plan)

        self.assertEqual(result["status"], "imported")
        self.assertEqual(result["nodes_merged"], 1)
        self.assertEqual(result["relationships_merged"], 1)
        self.assertGreaterEqual(mock_session.run.call_count, 3)

    def test_import_unavailable_when_driver_missing(self):
        with patch("app.services.graph.importer.get_neo4j_driver", return_value=None):
            result = import_cnas_graph(dry_run=False, plan=GraphPlan())

        self.assertEqual(result["status"], "unavailable")

    def test_import_failed_when_unique_name_constraint_is_violated(self):
        plan = GraphPlan(
            nodes=[
                NodeSpec(
                    label=LABEL_LOCATION,
                    key_property="name",
                    key_value="Mumbai",
                    properties={"source": "fir"},
                ),
                NodeSpec(
                    label=LABEL_LOCATION,
                    key_property="location_id",
                    key_value="Mumbai",
                    properties={"name": "Mumbai"},
                ),
            ]
        )

        class UniqueNameSession:
            def __init__(self):
                self.names: dict[str, str] = {}

            def run(self, query, **kwargs):
                return None

            def begin_transaction(self):
                return UniqueNameTransaction(self)

        class UniqueNameTransaction:
            def __init__(self, session: UniqueNameSession):
                self.session = session
                self._failed = False

            def run(self, query, **kwargs):
                if "Location" not in query or "row.key_value" not in query:
                    return
                prop = "name" if "{name:" in query else "location_id"
                for row in kwargs.get("rows") or []:
                    properties = dict(row.get("properties") or {})
                    name = properties.get("name") if prop != "name" else row["key_value"]
                    if not name:
                        continue
                    owner = self.session.names.get(name)
                    identity = f"{prop}:{row['key_value']}"
                    if owner is not None and owner != identity:
                        self._failed = True
                        raise RuntimeError(
                            "Node already exists with label Location and "
                            f"property name = '{name}'"
                        )
                    self.session.names[name] = identity

            def commit(self):
                if self._failed:
                    raise RuntimeError("cannot commit failed transaction")

            def rollback(self):
                return None

        result = import_cnas_graph(
            plan=plan,
            session_factory=lambda: _session_context(UniqueNameSession()),
        )
        self.assertEqual(result["status"], "failed")
        self.assertIn("name = 'Mumbai'", result["detail"])

    def test_unified_location_plan_imports_without_name_collision(self):
        now = "2026-01-01T00:00:00+00:00"
        plan = map_structured_import_records(
            persons=[
                {
                    "record_id": "import:person",
                    "source": "persons",
                    "content_hash": "a",
                    "ingested_at": now,
                    "data": {
                        "person_id": "P-IMPORT-1",
                        "name": "Import Person",
                    },
                }
            ],
            firs=[
                {
                    "record_id": "import:fir",
                    "source": "fir",
                    "content_hash": "b",
                    "ingested_at": now,
                    "data": {
                        "fir_id": "FIR-IMPORT-1",
                        "person_id": "P-IMPORT-1",
                        "location": "Mumbai",
                    },
                }
            ],
        )
        full_locations = [
            node for node in build_cnas_graph_plan().nodes if node.label == LABEL_LOCATION
        ]
        mumbai = next(
            node
            for node in full_locations
            if node.key_value == "Mumbai" and node.key_property == "name"
        )
        combined = GraphPlan(nodes=[*plan.nodes, mumbai], relationships=list(plan.relationships))

        class RecordingSession:
            def run(self, query, **kwargs):
                return None

            def begin_transaction(self):
                return RecordingTransaction()

        class RecordingTransaction:
            def run(self, query, **kwargs):
                return None

            def commit(self):
                return None

            def rollback(self):
                return None

        result = import_cnas_graph(
            plan=combined,
            session_factory=lambda: _session_context(RecordingSession()),
        )
        self.assertEqual(result["status"], "imported")
        self.assertFalse(unique_constraint_collisions(combined))


class Neo4jImportEndpointTests(unittest.TestCase):
    @patch("app.api.network.import_cnas_graph")
    def test_neo4j_import_endpoint(self, mock_import):
        from app.api.network import trigger_neo4j_import

        mock_import.return_value = {"status": "dry_run", "nodes": 10, "relationships": 20}

        result = trigger_neo4j_import(dry_run=True)

        self.assertEqual(result["status"], "dry_run")
        mock_import.assert_called_once_with(dry_run=True)


if __name__ == "__main__":
    unittest.main()
