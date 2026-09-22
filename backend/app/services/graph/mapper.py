"""Build a canonical CNAS graph plan from normalized ingestion records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.entity_resolution import CanonicalRegistry, build_canonical_registry
from app.services.extraction import (
    normalize_bank_account,
    normalize_phone,
    normalize_vehicle,
)
from app.services.graph.ontology import (
    CANONICAL_NODE_KEYS,
    LABEL_ACCOUNT,
    LABEL_CASE,
    LABEL_INCIDENT,
    LABEL_ORGANISATION,
    LABEL_BANK_ACCOUNT,
    LABEL_CRIME,
    LABEL_FIR,
    LABEL_LOCATION,
    LABEL_PERSON,
    LABEL_PHONE,
    LABEL_SOCIAL_ACCOUNT,
    LABEL_SURVEILLANCE_EVENT,
    LABEL_VEHICLE,
    REL_AT_LOCATION,
    REL_ASSOCIATED_WITH,
    REL_CALLED,
    REL_CO_ACCUSED_IN,
    REL_FOR_CRIME,
    REL_HAS_ACCOUNT,
    REL_HAS_PHONE,
    REL_HAS_SOCIAL_ACCOUNT,
    REL_INTERACTED_WITH,
    REL_INVOLVED_IN,
    REL_OBSERVED_AT,
    REL_OWNS,
    REL_PRESENT_AT,
    REL_SHARES_IDENTIFIER,
    REL_MEMBER_OF,
    REL_TRANSFERRED_MONEY_TO,
    REL_TRANSACTED_WITH,
    REL_USES,
    canonical_contract,
)
from app.services.ingestion import load_source_records
from app.services.normalization import NormalizedRecord


@dataclass(frozen=True)
class NodeSpec:
    label: str
    key_property: str
    key_value: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RelationshipSpec:
    rel_type: str
    from_label: str
    from_key: str
    from_value: str
    to_label: str
    to_key: str
    to_value: str
    record_id: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphPlan:
    nodes: list[NodeSpec] = field(default_factory=list)
    relationships: list[RelationshipSpec] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        node_counts: dict[str, int] = {}
        rel_counts: dict[str, int] = {}

        for node in self.nodes:
            node_counts[node.label] = node_counts.get(node.label, 0) + 1

        for rel in self.relationships:
            rel_counts[rel.rel_type] = rel_counts.get(rel.rel_type, 0) + 1

        return {
            "nodes": len(self.nodes),
            "relationships": len(self.relationships),
            "node_counts": node_counts,
            "relationship_counts": rel_counts,
        }

    def to_contract(self) -> dict[str, list[dict[str, Any]]]:
        """Serialize only the canonical projection using Appendix A.4 shape."""
        canonical_nodes = [node for node in self.nodes if node.label in CANONICAL_NODE_KEYS]
        canonical_rels = [rel for rel in self.relationships if rel.rel_type in {
            REL_CALLED, REL_USES, REL_TRANSACTED_WITH, REL_CO_ACCUSED_IN,
            REL_PRESENT_AT, REL_ASSOCIATED_WITH, REL_MEMBER_OF, REL_SHARES_IDENTIFIER,
        }]
        nodes_by_identity: dict[tuple[str, str], dict[str, Any]] = {}
        for node in canonical_nodes:
            identity = (node.label, node.key_value)
            existing = nodes_by_identity.get(identity)
            if existing is None:
                nodes_by_identity[identity] = {
                    "id": node.key_value,
                    "type": node.label,
                    "properties": node.properties,
                    "confidence": node.properties.get("confidence", 1.0),
                    "source_refs": [node.properties["source_ref"]] if node.properties.get("source_ref") else [],
                }
            elif node.properties.get("source_ref") and node.properties["source_ref"] not in existing["source_refs"]:
                existing["source_refs"].append(node.properties["source_ref"])
        nodes = list(nodes_by_identity.values())
        edges = [
            {
                "id": rel.record_id,
                "type": rel.rel_type,
                "from": rel.from_value,
                "to": rel.to_value,
                "properties": {
                    key: value for key, value in rel.properties.items()
                    if key not in {
                        "source_ref", "extraction_method", "confidence", "valid_from",
                        "valid_to", "ingested_at", "jurisdiction", "created_by",
                    }
                },
                **rel.properties,
            }
            for rel in canonical_rels
        ]
        return canonical_contract(nodes, edges)


def provenance(
    record: NormalizedRecord,
    source_ref: str | None = None,
    *,
    extraction_method: str = "structured",
    confidence: float = 1.0,
    valid_from: Any = None,
    valid_to: Any = None,
    jurisdiction: str | None = None,
    created_by: str = "system",
) -> dict[str, Any]:
    data = record["data"]
    return {
        "source": record["source"],
        "source_ref": source_ref or record["record_id"],
        "content_hash": record["content_hash"],
        "ingested_at": record["ingested_at"],
        "extraction_method": extraction_method,
        "confidence": confidence,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "jurisdiction": jurisdiction or data.get("jurisdiction"),
        "created_by": created_by,
    }


def _resolved_person_id(person_id: str | None, registry: CanonicalRegistry) -> str | None:
    if not person_id:
        return None
    person_key = str(person_id)
    if person_key in registry.person_names:
        return person_key
    return person_key


def _add_node(plan: GraphPlan, label: str, key_property: str, key_value: str, **properties: Any) -> None:
    if not key_value:
        return

    plan.nodes.append(
        NodeSpec(
            label=label,
            key_property=key_property,
            key_value=str(key_value),
            properties={key: value for key, value in properties.items() if value is not None},
        )
    )


def _add_location_node(
    plan: GraphPlan,
    location_key: str,
    record: NormalizedRecord,
    **properties: Any,
) -> None:
    """MERGE Location on ``name``, the unique Neo4j constraint.

    Canonical projection used to MERGE on ``location_id`` while SETting the
    same ``name``, which created a second Location node and aborted import
    with ``location_name_unique``.
    """
    key = str(location_key).strip()
    if not key:
        return
    _add_node(
        plan,
        LABEL_LOCATION,
        "name",
        key,
        location_id=key,
        **provenance(record),
        **properties,
    )


def _add_relationship(
    plan: GraphPlan,
    *,
    rel_type: str,
    from_label: str,
    from_key: str,
    from_value: str,
    to_label: str,
    to_key: str,
    to_value: str,
    record: NormalizedRecord,
    source_ref: str | None = None,
    **properties: Any,
) -> None:
    if not from_value or not to_value:
        return

    rel_props = provenance(record, source_ref=source_ref, **{
        key: properties.pop(key) for key in (
            "extraction_method", "confidence", "valid_from", "valid_to", "jurisdiction", "created_by",
        ) if key in properties
    })
    rel_props.update({key: value for key, value in properties.items() if value is not None})

    plan.relationships.append(
        RelationshipSpec(
            rel_type=rel_type,
            from_label=from_label,
            from_key=from_key,
            from_value=str(from_value),
            to_label=to_label,
            to_key=to_key,
            to_value=str(to_value),
            record_id=record["record_id"],
            properties=rel_props,
        )
    )


def _map_persons(plan: GraphPlan, records: list[NormalizedRecord], registry: CanonicalRegistry) -> None:
    for record in records:
        data = record["data"]
        person_id = _resolved_person_id(data.get("person_id"), registry)
        if not person_id:
            continue

        _add_node(
            plan,
            LABEL_PERSON,
            "person_id",
            person_id,
            name=data.get("name"),
            home_city=data.get("home_city"),
            risk_group=data.get("risk_group"),
            **provenance(record),
        )

        phone = data.get("phone")
        if phone:
            phone_value = normalize_phone(str(phone))
            _add_node(plan, LABEL_PHONE, "value", phone_value, **provenance(record))
            _add_relationship(
                plan,
                rel_type=REL_HAS_PHONE,
                from_label=LABEL_PERSON,
                from_key="person_id",
                from_value=person_id,
                to_label=LABEL_PHONE,
                to_key="value",
                to_value=phone_value,
                record=record,
            )

        bank_account = data.get("bank_account")
        if bank_account:
            account_id = normalize_bank_account(str(bank_account))
            _add_node(plan, LABEL_BANK_ACCOUNT, "account_id", account_id, **provenance(record))
            _add_relationship(
                plan,
                rel_type=REL_HAS_ACCOUNT,
                from_label=LABEL_PERSON,
                from_key="person_id",
                from_value=person_id,
                to_label=LABEL_BANK_ACCOUNT,
                to_key="account_id",
                to_value=account_id,
                record=record,
            )

        social_id = data.get("social_id")
        if social_id:
            handle = str(social_id).strip()
            _add_node(plan, LABEL_SOCIAL_ACCOUNT, "handle", handle, **provenance(record))
            _add_relationship(
                plan,
                rel_type=REL_HAS_SOCIAL_ACCOUNT,
                from_label=LABEL_PERSON,
                from_key="person_id",
                from_value=person_id,
                to_label=LABEL_SOCIAL_ACCOUNT,
                to_key="handle",
                to_value=handle,
                record=record,
            )

        vehicle_no = data.get("vehicle_no")
        if vehicle_no:
            vehicle_id = normalize_vehicle(str(vehicle_no))
            _add_node(
                plan,
                LABEL_VEHICLE,
                "vehicle_no",
                vehicle_id,
                **provenance(record),
            )
            _add_relationship(
                plan,
                rel_type=REL_OWNS,
                from_label=LABEL_PERSON,
                from_key="person_id",
                from_value=person_id,
                to_label=LABEL_VEHICLE,
                to_key="vehicle_no",
                to_value=vehicle_id,
                record=record,
            )


def _map_vehicles(plan: GraphPlan, records: list[NormalizedRecord], registry: CanonicalRegistry) -> None:
    for record in records:
        data = record["data"]
        vehicle_no = normalize_vehicle(str(data.get("vehicle_no") or ""))
        person_id = _resolved_person_id(data.get("person_id"), registry)
        if not vehicle_no or not person_id:
            continue

        _add_node(
            plan,
            LABEL_VEHICLE,
            "vehicle_no",
            vehicle_no,
            registered_city=data.get("registered_city"),
            vehicle_type=data.get("vehicle_type"),
            **provenance(record),
        )
        _add_relationship(
            plan,
            rel_type=REL_OWNS,
            from_label=LABEL_PERSON,
            from_key="person_id",
            from_value=person_id,
            to_label=LABEL_VEHICLE,
            to_key="vehicle_no",
            to_value=vehicle_no,
            record=record,
        )


def _map_entity_mapping(
    plan: GraphPlan,
    records: list[NormalizedRecord],
    registry: CanonicalRegistry,
) -> None:
    for record in records:
        data = record["data"]
        entity_id = _resolved_person_id(data.get("entity_id"), registry)
        entity_type = str(data.get("entity_type") or "").strip().lower()
        source_id = data.get("source_id")
        if not entity_id or not source_id:
            continue

        if entity_type == "person":
            _add_node(plan, LABEL_PERSON, "person_id", entity_id, **provenance(record))
            continue

        if entity_type == "phone":
            phone_value = normalize_phone(str(source_id))
            _add_node(plan, LABEL_PHONE, "value", phone_value, mapping_source=data.get("source"), **provenance(record))
            _add_relationship(
                plan,
                rel_type=REL_HAS_PHONE,
                from_label=LABEL_PERSON,
                from_key="person_id",
                from_value=entity_id,
                to_label=LABEL_PHONE,
                to_key="value",
                to_value=phone_value,
                record=record,
            )
        elif entity_type == "vehicle":
            vehicle_no = normalize_vehicle(str(source_id))
            _add_node(plan, LABEL_VEHICLE, "vehicle_no", vehicle_no, mapping_source=data.get("source"), **provenance(record))
            _add_relationship(
                plan,
                rel_type=REL_OWNS,
                from_label=LABEL_PERSON,
                from_key="person_id",
                from_value=entity_id,
                to_label=LABEL_VEHICLE,
                to_key="vehicle_no",
                to_value=vehicle_no,
                record=record,
            )
        elif entity_type == "bank_account":
            account_id = normalize_bank_account(str(source_id))
            _add_node(
                plan,
                LABEL_BANK_ACCOUNT,
                "account_id",
                account_id,
                mapping_source=data.get("source"),
                **provenance(record),
            )
            _add_relationship(
                plan,
                rel_type=REL_HAS_ACCOUNT,
                from_label=LABEL_PERSON,
                from_key="person_id",
                from_value=entity_id,
                to_label=LABEL_BANK_ACCOUNT,
                to_key="account_id",
                to_value=account_id,
                record=record,
            )
        elif entity_type == "social_account":
            handle = str(source_id).strip()
            _add_node(
                plan,
                LABEL_SOCIAL_ACCOUNT,
                "handle",
                handle,
                mapping_source=data.get("source"),
                **provenance(record),
            )
            _add_relationship(
                plan,
                rel_type=REL_HAS_SOCIAL_ACCOUNT,
                from_label=LABEL_PERSON,
                from_key="person_id",
                from_value=entity_id,
                to_label=LABEL_SOCIAL_ACCOUNT,
                to_key="handle",
                to_value=handle,
                record=record,
            )


def _map_cdr(plan: GraphPlan, records: list[NormalizedRecord], registry: CanonicalRegistry) -> None:
    for record in records:
        data = record["data"]
        caller_id = _resolved_person_id(data.get("caller_id"), registry)
        receiver_id = _resolved_person_id(data.get("receiver_id"), registry)
        if not caller_id or not receiver_id:
            continue

        _add_node(plan, LABEL_PERSON, "person_id", caller_id)
        _add_node(plan, LABEL_PERSON, "person_id", receiver_id)

        caller_phone = data.get("caller_phone")
        if caller_phone:
            phone_value = normalize_phone(str(caller_phone))
            _add_node(plan, LABEL_PHONE, "value", phone_value)
            _add_relationship(
                plan,
                rel_type=REL_HAS_PHONE,
                from_label=LABEL_PERSON,
                from_key="person_id",
                from_value=caller_id,
                to_label=LABEL_PHONE,
                to_key="value",
                to_value=phone_value,
                record=record,
                source_ref=f"{record['record_id']}:caller_phone",
            )

        receiver_phone = data.get("receiver_phone")
        if receiver_phone:
            phone_value = normalize_phone(str(receiver_phone))
            _add_node(plan, LABEL_PHONE, "value", phone_value)
            _add_relationship(
                plan,
                rel_type=REL_HAS_PHONE,
                from_label=LABEL_PERSON,
                from_key="person_id",
                from_value=receiver_id,
                to_label=LABEL_PHONE,
                to_key="value",
                to_value=phone_value,
                record=record,
                source_ref=f"{record['record_id']}:receiver_phone",
            )

        _add_relationship(
            plan,
            rel_type=REL_CALLED,
            from_label=LABEL_PERSON,
            from_key="person_id",
            from_value=caller_id,
            to_label=LABEL_PERSON,
            to_key="person_id",
            to_value=receiver_id,
            record=record,
            timestamp=data.get("timestamp"),
            duration_sec=data.get("duration_sec"),
            call_type=data.get("call_type"),
            caller_phone=caller_phone,
            receiver_phone=receiver_phone,
        )


def _map_finance(plan: GraphPlan, records: list[NormalizedRecord], registry: CanonicalRegistry) -> None:
    for record in records:
        data = record["data"]
        sender_id = _resolved_person_id(data.get("sender_id"), registry)
        receiver_id = _resolved_person_id(data.get("receiver_id"), registry)
        if not sender_id or not receiver_id:
            continue

        _add_node(plan, LABEL_PERSON, "person_id", sender_id)
        _add_node(plan, LABEL_PERSON, "person_id", receiver_id)

        sender_account = data.get("sender_account")
        if sender_account:
            account_id = normalize_bank_account(str(sender_account))
            _add_node(plan, LABEL_BANK_ACCOUNT, "account_id", account_id)
            _add_relationship(
                plan,
                rel_type=REL_HAS_ACCOUNT,
                from_label=LABEL_PERSON,
                from_key="person_id",
                from_value=sender_id,
                to_label=LABEL_BANK_ACCOUNT,
                to_key="account_id",
                to_value=account_id,
                record=record,
                source_ref=f"{record['record_id']}:sender_account",
            )

        receiver_account = data.get("receiver_account")
        if receiver_account:
            account_id = normalize_bank_account(str(receiver_account))
            _add_node(plan, LABEL_BANK_ACCOUNT, "account_id", account_id)
            _add_relationship(
                plan,
                rel_type=REL_HAS_ACCOUNT,
                from_label=LABEL_PERSON,
                from_key="person_id",
                from_value=receiver_id,
                to_label=LABEL_BANK_ACCOUNT,
                to_key="account_id",
                to_value=account_id,
                record=record,
                source_ref=f"{record['record_id']}:receiver_account",
            )

        _add_relationship(
            plan,
            rel_type=REL_TRANSFERRED_MONEY_TO,
            from_label=LABEL_PERSON,
            from_key="person_id",
            from_value=sender_id,
            to_label=LABEL_PERSON,
            to_key="person_id",
            to_value=receiver_id,
            record=record,
            amount=data.get("amount"),
            date=data.get("date"),
            sender_account=sender_account,
            receiver_account=receiver_account,
        )


def _map_fir(plan: GraphPlan, records: list[NormalizedRecord], registry: CanonicalRegistry) -> None:
    for record in records:
        data = record["data"]
        fir_id = data.get("fir_id")
        person_id = _resolved_person_id(data.get("person_id"), registry)
        crime_name = data.get("crime")
        location_name = data.get("location")
        if not fir_id or not person_id:
            continue

        _add_node(
            plan,
            LABEL_FIR,
            "fir_id",
            str(fir_id),
            date=data.get("date"),
            **provenance(record),
        )
        _add_node(plan, LABEL_PERSON, "person_id", person_id)

        if crime_name:
            crime_key = str(crime_name).strip()
            _add_node(plan, LABEL_CRIME, "name", crime_key, **provenance(record))
            _add_relationship(
                plan,
                rel_type=REL_FOR_CRIME,
                from_label=LABEL_FIR,
                from_key="fir_id",
                from_value=str(fir_id),
                to_label=LABEL_CRIME,
                to_key="name",
                to_value=crime_key,
                record=record,
                source_ref=f"{record['record_id']}:crime",
            )

        if location_name:
            location_key = str(location_name).strip()
            _add_location_node(plan, location_key, record)
            _add_relationship(
                plan,
                rel_type=REL_AT_LOCATION,
                from_label=LABEL_FIR,
                from_key="fir_id",
                from_value=str(fir_id),
                to_label=LABEL_LOCATION,
                to_key="name",
                to_value=location_key,
                record=record,
                source_ref=f"{record['record_id']}:location",
            )

        _add_relationship(
            plan,
            rel_type=REL_INVOLVED_IN,
            from_label=LABEL_PERSON,
            from_key="person_id",
            from_value=person_id,
            to_label=LABEL_FIR,
            to_key="fir_id",
            to_value=str(fir_id),
            record=record,
        )


def _social_rel_type(interaction_type: str | None) -> str:
    if not interaction_type:
        return REL_INTERACTED_WITH
    return f"SOCIAL_{str(interaction_type).upper()}"


def _map_social(plan: GraphPlan, records: list[NormalizedRecord], registry: CanonicalRegistry) -> None:
    for record in records:
        data = record["data"]
        user_id = _resolved_person_id(data.get("user_id"), registry)
        connected_user_id = _resolved_person_id(data.get("connected_user_id"), registry)
        if not user_id or not connected_user_id:
            continue

        _add_node(plan, LABEL_PERSON, "person_id", user_id)
        _add_node(plan, LABEL_PERSON, "person_id", connected_user_id)

        user_handle = data.get("user_handle")
        if user_handle:
            handle = str(user_handle).strip()
            _add_node(plan, LABEL_SOCIAL_ACCOUNT, "handle", handle)
            _add_relationship(
                plan,
                rel_type=REL_HAS_SOCIAL_ACCOUNT,
                from_label=LABEL_PERSON,
                from_key="person_id",
                from_value=user_id,
                to_label=LABEL_SOCIAL_ACCOUNT,
                to_key="handle",
                to_value=handle,
                record=record,
                source_ref=f"{record['record_id']}:user_handle",
            )

        connected_handle = data.get("connected_handle")
        if connected_handle:
            handle = str(connected_handle).strip()
            _add_node(plan, LABEL_SOCIAL_ACCOUNT, "handle", handle)
            _add_relationship(
                plan,
                rel_type=REL_HAS_SOCIAL_ACCOUNT,
                from_label=LABEL_PERSON,
                from_key="person_id",
                from_value=connected_user_id,
                to_label=LABEL_SOCIAL_ACCOUNT,
                to_key="handle",
                to_value=handle,
                record=record,
                source_ref=f"{record['record_id']}:connected_handle",
            )

        rel_type = _social_rel_type(data.get("interaction_type"))
        _add_relationship(
            plan,
            rel_type=rel_type,
            from_label=LABEL_PERSON,
            from_key="person_id",
            from_value=user_id,
            to_label=LABEL_PERSON,
            to_key="person_id",
            to_value=connected_user_id,
            record=record,
            date=data.get("date"),
            interaction_type=data.get("interaction_type"),
            user_handle=user_handle,
            connected_handle=connected_handle,
        )


def _map_surveillance(plan: GraphPlan, records: list[NormalizedRecord], registry: CanonicalRegistry) -> None:
    for record in records:
        data = record["data"]
        event_id = data.get("event_id")
        person_id = _resolved_person_id(data.get("person_id"), registry)
        location_name = data.get("location")
        if not event_id or not person_id:
            continue

        _add_node(
            plan,
            LABEL_SURVEILLANCE_EVENT,
            "event_id",
            str(event_id),
            timestamp=data.get("timestamp"),
            event_type=data.get("event_type"),
            event_source=data.get("source"),
            vehicle_no=data.get("vehicle_no"),
            **provenance(record),
        )
        _add_node(plan, LABEL_PERSON, "person_id", person_id)

        vehicle_no = data.get("vehicle_no")
        if vehicle_no:
            vehicle_id = normalize_vehicle(str(vehicle_no))
            _add_node(plan, LABEL_VEHICLE, "vehicle_no", vehicle_id)
            _add_relationship(
                plan,
                rel_type=REL_OWNS,
                from_label=LABEL_PERSON,
                from_key="person_id",
                from_value=person_id,
                to_label=LABEL_VEHICLE,
                to_key="vehicle_no",
                to_value=vehicle_id,
                record=record,
                source_ref=f"{record['record_id']}:vehicle_no",
            )

        _add_relationship(
            plan,
            rel_type=REL_OBSERVED_AT,
            from_label=LABEL_PERSON,
            from_key="person_id",
            from_value=person_id,
            to_label=LABEL_SURVEILLANCE_EVENT,
            to_key="event_id",
            to_value=str(event_id),
            record=record,
        )

        if location_name:
            location_key = str(location_name).strip()
            _add_location_node(plan, location_key, record)
            _add_relationship(
                plan,
                rel_type=REL_AT_LOCATION,
                from_label=LABEL_SURVEILLANCE_EVENT,
                from_key="event_id",
                from_value=str(event_id),
                to_label=LABEL_LOCATION,
                to_key="name",
                to_value=location_key,
                record=record,
                source_ref=f"{record['record_id']}:event_location",
            )
            _add_relationship(
                plan,
                rel_type=REL_PRESENT_AT,
                from_label=LABEL_PERSON,
                from_key="person_id",
                from_value=person_id,
                to_label=LABEL_LOCATION,
                to_key="name",
                to_value=location_key,
                record=record,
                source_ref=f"{record['record_id']}:present_at",
                timestamp=data.get("timestamp"),
                event_type=data.get("event_type"),
            )


def _canonical_node(
    plan: GraphPlan,
    label: str,
    key_property: str,
    key_value: Any,
    record: NormalizedRecord,
    **properties: Any,
) -> None:
    if key_value is None or str(key_value).strip() == "":
        return
    _add_node(
        plan,
        label,
        key_property,
        str(key_value),
        source_ref=record["record_id"],
        source_refs=[record["record_id"]],
        confidence=1.0,
        **properties,
    )


def _canonical_relationship(
    plan: GraphPlan,
    *,
    rel_type: str,
    from_label: str,
    from_key: str,
    from_value: Any,
    to_label: str,
    to_key: str,
    to_value: Any,
    record: NormalizedRecord,
    source_ref: str | None = None,
    extraction_method: str = "structured",
    confidence: float = 1.0,
    valid_from: Any = None,
    valid_to: Any = None,
    jurisdiction: str | None = None,
    created_by: str = "system",
    **properties: Any,
) -> None:
    _add_relationship(
        plan,
        rel_type=rel_type,
        from_label=from_label,
        from_key=from_key,
        from_value=str(from_value) if from_value is not None else "",
        to_label=to_label,
        to_key=to_key,
        to_value=str(to_value) if to_value is not None else "",
        record=record,
        source_ref=source_ref,
        extraction_method=extraction_method,
        confidence=confidence,
        valid_from=valid_from,
        valid_to=valid_to,
        jurisdiction=jurisdiction,
        created_by=created_by,
        **properties,
    )


def _map_canonical_projection(
    plan: GraphPlan,
    records_by_source: dict[str, list[NormalizedRecord]],
    registry: CanonicalRegistry,
) -> None:
    """Emit the Appendix A projection while retaining the legacy projection."""
    identifiers: dict[str, dict[str, list[tuple[str, NormalizedRecord]]]] = {
        "phone": {}, "vehicle": {}, "account": {},
    }
    for record in records_by_source["persons"]:
        data = record["data"]
        person_id = _resolved_person_id(data.get("person_id"), registry)
        if not person_id:
            continue
        _canonical_node(plan, LABEL_PERSON, "person_id", person_id, record, name=data.get("name"), aliases=[])
        for kind, raw, label, key, normalizer in (
            ("phone", data.get("phone"), LABEL_PHONE, "msisdn", normalize_phone),
            ("vehicle", data.get("vehicle_no"), LABEL_VEHICLE, "registration_no", normalize_vehicle),
            ("account", data.get("bank_account"), LABEL_ACCOUNT, "account_ref", normalize_bank_account),
        ):
            if not raw:
                continue
            value = normalizer(str(raw))
            identifiers[kind].setdefault(value, []).append((person_id, record))
            _canonical_node(plan, label, key, value, record)
            _canonical_relationship(
                plan,
                rel_type=REL_USES,
                from_label=LABEL_PERSON,
                from_key="person_id",
                from_value=person_id,
                to_label=label,
                to_key=key,
                to_value=value,
                record=record,
                attribution_basis="persons_source",
            )

    for shared_type, by_value in identifiers.items():
        for shared_value, people in by_value.items():
            for index, (left, left_record) in enumerate(people):
                for right, _ in people[index + 1:]:
                    _canonical_relationship(
                        plan,
                        rel_type=REL_SHARES_IDENTIFIER,
                        from_label=LABEL_PERSON,
                        from_key="person_id",
                        from_value=left,
                        to_label=LABEL_PERSON,
                        to_key="person_id",
                        to_value=right,
                        record=left_record,
                        source_ref=f"{left_record['record_id']}:{shared_type}:{shared_value}",
                        extraction_method="inferred",
                        confidence=0.95,
                        shared_type=shared_type,
                        shared_value=shared_value,
                        temporal_overlap=None,
                    )

    for record in records_by_source["cdr"]:
        data = record["data"]
        caller = normalize_phone(str(data.get("caller_phone") or ""))
        receiver = normalize_phone(str(data.get("receiver_phone") or ""))
        if not caller or not receiver:
            continue
        _canonical_node(plan, LABEL_PHONE, "msisdn", caller, record)
        _canonical_node(plan, LABEL_PHONE, "msisdn", receiver, record)
        _canonical_relationship(
            plan, rel_type=REL_CALLED,
            from_label=LABEL_PHONE, from_key="msisdn", from_value=caller,
            to_label=LABEL_PHONE, to_key="msisdn", to_value=receiver,
            record=record, valid_from=data.get("timestamp"),
            call_count=1, total_duration=data.get("duration_sec"),
            first_call=data.get("timestamp"), last_call=data.get("timestamp"),
            direction="outbound",
        )

    for record in records_by_source["finance"]:
        data = record["data"]
        sender = normalize_bank_account(str(data.get("sender_account") or ""))
        receiver = normalize_bank_account(str(data.get("receiver_account") or ""))
        if not sender or not receiver:
            continue
        _canonical_node(plan, LABEL_ACCOUNT, "account_ref", sender, record)
        _canonical_node(plan, LABEL_ACCOUNT, "account_ref", receiver, record)
        _canonical_relationship(
            plan, rel_type=REL_TRANSACTED_WITH,
            from_label=LABEL_ACCOUNT, from_key="account_ref", from_value=sender,
            to_label=LABEL_ACCOUNT, to_key="account_ref", to_value=receiver,
            record=record, valid_from=data.get("date"), amount=data.get("amount"),
            txn_ref=record["record_id"], txn_datetime=data.get("date"), mode=None,
        )

    for record in records_by_source["fir"]:
        data = record["data"]
        case_no = data.get("fir_id")
        person_id = _resolved_person_id(data.get("person_id"), registry)
        location = str(data.get("location") or "").strip()
        if not case_no or not person_id:
            continue
        _canonical_node(plan, LABEL_CASE, "case_no", case_no, record, fir_no=case_no, status=None)
        _canonical_node(plan, LABEL_INCIDENT, "incident_id", f"{case_no}:incident", record, type=data.get("crime"), occurred_at=data.get("date"), case_no=case_no)
        _canonical_relationship(
            plan, rel_type=REL_CO_ACCUSED_IN,
            from_label=LABEL_PERSON, from_key="person_id", from_value=person_id,
            to_label=LABEL_CASE, to_key="case_no", to_value=case_no,
            record=record, valid_from=data.get("date"), role=None, sections=[],
        )
        if location:
            _canonical_node(
                plan,
                LABEL_LOCATION,
                "name",
                location,
                record,
                location_id=location,
                type="unknown",
                jurisdiction=None,
            )

    for record in records_by_source["social"]:
        data = record["data"]
        left = _resolved_person_id(data.get("user_id"), registry)
        right = _resolved_person_id(data.get("connected_user_id"), registry)
        if left and right:
            _canonical_relationship(
                plan, rel_type=REL_ASSOCIATED_WITH,
                from_label=LABEL_PERSON, from_key="person_id", from_value=left,
                to_label=LABEL_PERSON, to_key="person_id", to_value=right,
                record=record, valid_from=data.get("date"),
                association_type=data.get("interaction_type"), observed_by=record["source"],
            )

    for record in records_by_source["surveillance"]:
        data = record["data"]
        person_id = _resolved_person_id(data.get("person_id"), registry)
        location = str(data.get("location") or "").strip()
        if not person_id or not location:
            continue
        _canonical_node(
            plan,
            LABEL_LOCATION,
            "name",
            location,
            record,
            location_id=location,
            type="unknown",
            jurisdiction=None,
        )
        _canonical_relationship(
            plan, rel_type=REL_PRESENT_AT,
            from_label=LABEL_PERSON, from_key="person_id", from_value=person_id,
            to_label=LABEL_LOCATION, to_key="name", to_value=location,
            record=record, valid_from=data.get("timestamp"), observed_at=data.get("timestamp"),
            observation_type=data.get("event_type"),
        )
        vehicle = normalize_vehicle(str(data.get("vehicle_no") or ""))
        if vehicle:
            _canonical_node(plan, LABEL_VEHICLE, "registration_no", vehicle, record)
            _canonical_relationship(
                plan, rel_type=REL_PRESENT_AT,
                from_label=LABEL_VEHICLE, from_key="registration_no", from_value=vehicle,
                to_label=LABEL_LOCATION, to_key="name", to_value=location,
                record=record, valid_from=data.get("timestamp"), observed_at=data.get("timestamp"),
                observation_type=data.get("event_type"),
            )


def build_cnas_graph_plan(registry: CanonicalRegistry | None = None) -> GraphPlan:
    """Build the canonical CNAS graph import plan from normalized source records."""
    active_registry = registry or build_canonical_registry()
    plan = GraphPlan()

    records_by_source = {source: load_source_records(source) for source in (
        "persons",
        "vehicles",
        "entity_mapping",
        "cdr",
        "finance",
        "fir",
        "social",
        "surveillance",
    )}

    _map_persons(plan, records_by_source["persons"], active_registry)
    _map_vehicles(plan, records_by_source["vehicles"], active_registry)
    _map_entity_mapping(plan, records_by_source["entity_mapping"], active_registry)
    _map_cdr(plan, records_by_source["cdr"], active_registry)
    _map_finance(plan, records_by_source["finance"], active_registry)
    _map_fir(plan, records_by_source["fir"], active_registry)
    _map_social(plan, records_by_source["social"], active_registry)
    _map_surveillance(plan, records_by_source["surveillance"], active_registry)
    _map_canonical_projection(plan, records_by_source, active_registry)

    return plan


def map_entity_mapping_records(
    records: list[NormalizedRecord],
    registry: CanonicalRegistry | None = None,
) -> GraphPlan:
    """Project entity-mapping rows through the existing mapping mapper."""
    plan = GraphPlan()
    _map_entity_mapping(plan, records, registry or build_canonical_registry())
    return plan


def map_structured_import_records(
    *,
    persons: list[NormalizedRecord] | None = None,
    firs: list[NormalizedRecord] | None = None,
    vehicles: list[NormalizedRecord] | None = None,
    registry: CanonicalRegistry | None = None,
) -> GraphPlan:
    """Project imported structured records through the existing graph mappers."""
    active_registry = registry or build_canonical_registry()
    plan = GraphPlan()
    if persons:
        _map_persons(plan, persons, active_registry)
    if vehicles:
        _map_vehicles(plan, vehicles, active_registry)
    if firs:
        _map_fir(plan, firs, active_registry)
    return plan
