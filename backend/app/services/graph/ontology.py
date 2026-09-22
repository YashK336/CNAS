"""CNAS graph ontology and the frozen SUTRADHAAR canonical contract.

Legacy labels and relationship names remain exported for compatibility with
the existing API and persisted graph. New imports also emit the canonical
projection defined by the architecture document.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

# Node labels
LABEL_PERSON = "Person"
LABEL_PHONE = "Phone"
LABEL_VEHICLE = "Vehicle"
LABEL_BANK_ACCOUNT = "BankAccount"
LABEL_SOCIAL_ACCOUNT = "SocialAccount"
LABEL_LOCATION = "Location"
LABEL_FIR = "FIR"
LABEL_CRIME = "Crime"
LABEL_SURVEILLANCE_EVENT = "SurveillanceEvent"

# SUTRADHAAR canonical node labels.  These are deliberately separate from
# legacy labels so existing graph consumers can migrate without a flag day.
LABEL_ACCOUNT = "Account"
LABEL_ORGANISATION = "Organisation"
LABEL_CASE = "Case"
LABEL_INCIDENT = "Incident"

ALL_NODE_LABELS = (
    LABEL_PERSON,
    LABEL_PHONE,
    LABEL_VEHICLE,
    LABEL_BANK_ACCOUNT,
    LABEL_SOCIAL_ACCOUNT,
    LABEL_LOCATION,
    LABEL_FIR,
    LABEL_CRIME,
    LABEL_SURVEILLANCE_EVENT,
    LABEL_ACCOUNT,
    LABEL_ORGANISATION,
    LABEL_CASE,
    LABEL_INCIDENT,
)

# Relationship types supported by canonical CNAS datasets
REL_HAS_PHONE = "HAS_PHONE"
REL_OWNS = "OWNS"
REL_HAS_ACCOUNT = "HAS_ACCOUNT"
REL_HAS_SOCIAL_ACCOUNT = "HAS_SOCIAL_ACCOUNT"
REL_CALLED = "CALLED"
REL_TRANSFERRED_MONEY_TO = "TRANSFERRED_MONEY_TO"
REL_INTERACTED_WITH = "INTERACTED_WITH"
REL_INVOLVED_IN = "INVOLVED_IN"
REL_FOR_CRIME = "FOR_CRIME"
REL_AT_LOCATION = "AT_LOCATION"
REL_OBSERVED_AT = "OBSERVED_AT"
REL_PRESENT_AT = "PRESENT_AT"

# Canonical relationship vocabulary from Appendix A of SUTRADHAAR.
REL_USES = "USES"
REL_TRANSACTED_WITH = "TRANSACTED_WITH"
REL_CO_ACCUSED_IN = "CO_ACCUSED_IN"
REL_ASSOCIATED_WITH = "ASSOCIATED_WITH"
REL_MEMBER_OF = "MEMBER_OF"
REL_SHARES_IDENTIFIER = "SHARES_IDENTIFIER"

CANONICAL_RELATIONSHIP_TYPES = frozenset(
    {
        REL_CALLED,
        REL_USES,
        REL_TRANSACTED_WITH,
        REL_CO_ACCUSED_IN,
        REL_PRESENT_AT,
        REL_ASSOCIATED_WITH,
        REL_MEMBER_OF,
        REL_SHARES_IDENTIFIER,
    }
)

MANDATORY_EDGE_PROVENANCE_FIELDS = (
    "source_ref",
    "extraction_method",
    "confidence",
    "valid_from",
    "valid_to",
    "ingested_at",
    "jurisdiction",
    "created_by",
)

CANONICAL_NODE_KEYS: dict[str, str] = {
    LABEL_PERSON: "person_id",
    LABEL_PHONE: "msisdn",
    LABEL_VEHICLE: "registration_no",
    LABEL_ACCOUNT: "account_ref",
    LABEL_LOCATION: "location_id",
    LABEL_ORGANISATION: "org_id",
    LABEL_CASE: "case_no",
    LABEL_INCIDENT: "incident_id",
}

# Uniqueness constraints: (label, property)
UNIQUE_CONSTRAINTS: tuple[tuple[str, str], ...] = (
    (LABEL_PERSON, "person_id"),
    (LABEL_PHONE, "value"),
    (LABEL_VEHICLE, "vehicle_no"),
    (LABEL_BANK_ACCOUNT, "account_id"),
    (LABEL_SOCIAL_ACCOUNT, "handle"),
    (LABEL_LOCATION, "name"),
    (LABEL_FIR, "fir_id"),
    (LABEL_CRIME, "name"),
    (LABEL_SURVEILLANCE_EVENT, "event_id"),
)

# Applied by the migration/import path in addition to the legacy list. The
# legacy ``UNIQUE_CONSTRAINTS`` tuple remains stable for existing callers.
CANONICAL_UNIQUE_CONSTRAINTS: tuple[tuple[str, str], ...] = (
    (LABEL_ACCOUNT, "account_ref"),
    (LABEL_ORGANISATION, "org_id"),
    (LABEL_CASE, "case_no"),
    (LABEL_INCIDENT, "incident_id"),
)

# Canonical ingestion sources included in the Neo4j import (excludes external datasets).
IMPORT_SOURCES: tuple[str, ...] = (
    "persons",
    "vehicles",
    "entity_mapping",
    "cdr",
    "finance",
    "fir",
    "social",
    "surveillance",
)


def validate_edge_provenance(properties: Mapping[str, Any]) -> None:
    """Reject canonical edges that cannot be explained or time-scoped.

    Upstream datasets currently omit jurisdiction and temporal end dates. The
    keys are still present with ``None`` and are reported in the contract;
    source_ref and extraction_method are the non-null write-time minimum.
    """
    missing = [field for field in MANDATORY_EDGE_PROVENANCE_FIELDS if field not in properties]
    if missing:
        raise ValueError(f"Missing mandatory edge provenance fields: {', '.join(missing)}")
    if not properties["source_ref"]:
        raise ValueError("Canonical edges require a non-empty source_ref")
    if not properties["extraction_method"]:
        raise ValueError("Canonical edges require a non-empty extraction_method")


def canonical_contract(nodes: Iterable[Mapping[str, Any]], edges: Iterable[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Return and validate the frozen JSON-compatible node/edge contract."""
    node_list = [dict(node) for node in nodes]
    edge_list = [dict(edge) for edge in edges]
    for edge in edge_list:
        validate_edge_provenance(edge)
    return {"nodes": node_list, "edges": edge_list}
