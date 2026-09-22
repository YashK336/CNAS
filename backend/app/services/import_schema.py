"""Flexible investigative-field catalog and header mapping for data import.

Does not require uploaders to match the CNAS CSV schema. Unknown columns stay
unmapped and are retained as source data. Mapping is suggested, never forced.
"""

from __future__ import annotations

import re
from typing import Any

from rapidfuzz import fuzz

CNAS_FIELDS: tuple[dict[str, str], ...] = (
    {
        "id": "fir_id",
        "label": "FIR / Case ID",
        "group": "case",
        "description": "Case or FIR identifier.",
    },
    {
        "id": "person_id",
        "label": "Person ID",
        "group": "person",
        "description": "Existing CNAS person identifier, if known.",
    },
    {
        "id": "name",
        "label": "Person",
        "group": "person",
        "description": "Suspect, accused, or involved person name.",
    },
    {
        "id": "phone",
        "label": "Phone",
        "group": "identifier",
        "description": "Mobile or other telephone number.",
    },
    {
        "id": "vehicle_no",
        "label": "Vehicle",
        "group": "identifier",
        "description": "Vehicle registration mark.",
    },
    {
        "id": "bank_account",
        "label": "Bank account",
        "group": "identifier",
        "description": "Bank or account reference.",
    },
    {
        "id": "social_id",
        "label": "Social account",
        "group": "identifier",
        "description": "Social-media handle or account id.",
    },
    {
        "id": "jurisdiction",
        "label": "Jurisdiction",
        "group": "place",
        "description": "Owning jurisdiction or district used for access control.",
    },
    {
        "id": "home_city",
        "label": "Home city",
        "group": "place",
        "description": "Person home city.",
    },
    {
        "id": "location",
        "label": "Location",
        "group": "place",
        "description": "Incident or event location.",
    },
    {
        "id": "date",
        "label": "Event date",
        "group": "event",
        "description": "Incident, FIR, or event date.",
    },
    {
        "id": "crime",
        "label": "Crime / offence",
        "group": "event",
        "description": "Offence or crime type.",
    },
    {
        "id": "vehicle_type",
        "label": "Vehicle type",
        "group": "identifier",
        "description": "Car, motorcycle, or other vehicle class.",
    },
    {
        "id": "registered_city",
        "label": "Vehicle registered city",
        "group": "place",
        "description": "City of vehicle registration.",
    },
    {
        "id": "risk_group",
        "label": "Risk group",
        "group": "person",
        "description": "Existing risk band, if the source already carries one.",
    },
    {
        "id": "narrative_text",
        "label": "Narrative / notes",
        "group": "narrative",
        "description": "Free text sent through unstructured extraction.",
    },
    {
        "id": "source_ref",
        "label": "Source reference",
        "group": "provenance",
        "description": "External document or FIR reference for unstructured text.",
    },
)

FIELD_IDS = frozenset(field["id"] for field in CNAS_FIELDS)

# Normalized header → CNAS field. Exact alias wins over fuzzy match.
FIELD_ALIASES: dict[str, str] = {
    "fir_id": "fir_id",
    "fir": "fir_id",
    "fir no": "fir_id",
    "fir no.": "fir_id",
    "fir number": "fir_id",
    "fir_number": "fir_id",
    "case number": "fir_id",
    "case no": "fir_id",
    "case no.": "fir_id",
    "case_id": "fir_id",
    "case id": "fir_id",
    "caseno": "fir_id",
    "crime number": "fir_id",
    "person_id": "person_id",
    "person id": "person_id",
    "accused_id": "person_id",
    "suspect_id": "person_id",
    "name": "name",
    "person": "name",
    "person name": "name",
    "suspect name": "name",
    "suspect": "name",
    "accused": "name",
    "accused name": "name",
    "full name": "name",
    "phone": "phone",
    "phone number": "phone",
    "mobile": "phone",
    "mobile no": "phone",
    "mobile no.": "phone",
    "mobile number": "phone",
    "contact": "phone",
    "contact no": "phone",
    "msisdn": "phone",
    "vehicle_no": "vehicle_no",
    "vehicle no": "vehicle_no",
    "vehicle number": "vehicle_no",
    "vehicle registration": "vehicle_no",
    "registration no": "vehicle_no",
    "registration number": "vehicle_no",
    "reg no": "vehicle_no",
    "vahan": "vehicle_no",
    "vehicle": "vehicle_no",
    "bank_account": "bank_account",
    "bank account": "bank_account",
    "account": "bank_account",
    "account no": "bank_account",
    "a/c": "bank_account",
    "social_id": "social_id",
    "social": "social_id",
    "handle": "social_id",
    "jurisdiction": "jurisdiction",
    "district": "jurisdiction",
    "ps": "jurisdiction",
    "police station": "jurisdiction",
    "home_city": "home_city",
    "home city": "home_city",
    "city": "home_city",
    "location": "location",
    "place": "location",
    "scene": "location",
    "incident location": "location",
    "date": "date",
    "incident date": "date",
    "event date": "date",
    "fir date": "date",
    "occurrence date": "date",
    "crime": "crime",
    "offence": "crime",
    "offense": "crime",
    "ipc": "crime",
    "charge": "crime",
    "vehicle_type": "vehicle_type",
    "vehicle type": "vehicle_type",
    "registered_city": "registered_city",
    "registered city": "registered_city",
    "risk_group": "risk_group",
    "risk group": "risk_group",
    "risk": "risk_group",
    "narrative_text": "narrative_text",
    "narrative": "narrative_text",
    "text": "narrative_text",
    "statement": "narrative_text",
    "source_ref": "source_ref",
    "source ref": "source_ref",
    "source": "source_ref",
    "document id": "source_ref",
}

UNMAPPED_NOTICE = (
    "CNAS does not currently map this field. The original value will be "
    "retained as source data where supported."
)

FUZZY_ACCEPT_SCORE = 86
FUZZY_SUGGEST_SCORE = 72

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_header(value: str) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("&", " and ")
    return _NON_ALNUM.sub(" ", text).strip()


def field_catalog() -> list[dict[str, str]]:
    return [dict(field) for field in CNAS_FIELDS]


def _alias_target(header: str) -> str | None:
    key = normalize_header(header)
    if not key:
        return None
    if key in FIELD_ALIASES:
        return FIELD_ALIASES[key]
    compact = key.replace(" ", "")
    for alias, field_id in FIELD_ALIASES.items():
        if alias.replace(" ", "") == compact:
            return field_id
    return None


def _fuzzy_target(header: str, claimed: set[str]) -> tuple[str | None, int]:
    key = normalize_header(header)
    if not key:
        return None, 0

    labels: list[tuple[str, str]] = []
    for field in CNAS_FIELDS:
        labels.append((field["id"], field["id"].replace("_", " ")))
        labels.append((field["id"], field["label"].lower()))
    for alias, field_id in FIELD_ALIASES.items():
        labels.append((field_id, alias))

    best_id: str | None = None
    best_score = 0
    for field_id, label in labels:
        if field_id in claimed:
            continue
        score = int(fuzz.token_sort_ratio(key, label))
        if score > best_score:
            best_id = field_id
            best_score = score
    return best_id, best_score


def suggest_mappings(columns: list[str]) -> list[dict[str, Any]]:
    """Return per-column mapping suggestions. Duplicate targets keep the first hit."""
    claimed: set[str] = set()
    suggestions: list[dict[str, Any]] = []

    for column in columns:
        alias = _alias_target(column)
        if alias and alias not in claimed:
            claimed.add(alias)
            suggestions.append(
                {
                    "column": column,
                    "cnas_field": alias,
                    "confidence": 1.0,
                    "status": "mapped",
                    "method": "alias",
                    "notice": None,
                }
            )
            continue

        fuzzy_id, score = _fuzzy_target(column, claimed)
        if fuzzy_id and score >= FUZZY_ACCEPT_SCORE:
            claimed.add(fuzzy_id)
            suggestions.append(
                {
                    "column": column,
                    "cnas_field": fuzzy_id,
                    "confidence": round(score / 100, 2),
                    "status": "mapped",
                    "method": "fuzzy",
                    "notice": None,
                }
            )
            continue

        notice = UNMAPPED_NOTICE
        if fuzzy_id and score >= FUZZY_SUGGEST_SCORE:
            notice = (
                f"{UNMAPPED_NOTICE} Closest CNAS field is "
                f"'{fuzzy_id}' ({score}% similar) — confirm before mapping."
            )

        suggestions.append(
            {
                "column": column,
                "cnas_field": None,
                "confidence": round(score / 100, 2) if fuzzy_id else 0.0,
                "status": "unmapped",
                "method": "none",
                "suggested_field": fuzzy_id if score >= FUZZY_SUGGEST_SCORE else None,
                "notice": notice,
            }
        )

    return suggestions


def apply_user_mappings(
    columns: list[str],
    user_mappings: dict[str, str | None] | None,
) -> list[dict[str, Any]]:
    """Merge investigator overrides onto detected suggestions.

    Empty / ``unmapped`` values leave the column unmapped. Unknown CNAS field
    ids are ignored so a stale UI cannot invent targets.
    """
    suggestions = {item["column"]: item for item in suggest_mappings(columns)}
    if not user_mappings:
        return [suggestions[column] for column in columns]

    claimed: set[str] = set()
    result: list[dict[str, Any]] = []

    for column in columns:
        raw = user_mappings.get(column, _SENTINEL)
        current = dict(suggestions[column])
        if raw is _SENTINEL:
            field_id = current.get("cnas_field")
            if isinstance(field_id, str) and field_id in claimed:
                current["cnas_field"] = None
                current["status"] = "unmapped"
                current["notice"] = UNMAPPED_NOTICE
            elif isinstance(field_id, str):
                claimed.add(field_id)
            result.append(current)
            continue

        if raw in {None, "", "unmapped"}:
            current["cnas_field"] = None
            current["status"] = "unmapped"
            current["confidence"] = 0.0
            current["method"] = "user"
            current["notice"] = UNMAPPED_NOTICE
            result.append(current)
            continue

        field_id = str(raw).strip()
        if field_id not in FIELD_IDS:
            current["cnas_field"] = None
            current["status"] = "unmapped"
            current["method"] = "user"
            current["notice"] = (
                f"'{field_id}' is not a CNAS field. {UNMAPPED_NOTICE}"
            )
            result.append(current)
            continue

        current["cnas_field"] = field_id
        current["status"] = "mapped"
        current["confidence"] = 1.0
        current["method"] = "user"
        current["notice"] = None
        claimed.add(field_id)
        result.append(current)

    return result


_SENTINEL = object()


def mapping_lookup(mappings: list[dict[str, Any]]) -> dict[str, str]:
    """Column → CNAS field for mapped columns only."""
    return {
        item["column"]: item["cnas_field"]
        for item in mappings
        if item.get("cnas_field")
    }
