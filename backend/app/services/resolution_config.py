"""
Thresholds and labels for entity resolution.

Identifier matches are exact and deterministic. Name matches use rapidfuzz
scores on a 0-100 scale.
"""

from __future__ import annotations

# Exact identifier lookups always resolve at this confidence.
IDENTIFIER_MATCH_CONFIDENCE = 1.0

# Minimum combined fuzzy name score required for a resolved match.
NAME_RESOLVED_MIN_SCORE = 92.0

# Minimum score for a name to be considered a candidate during ambiguity checks.
NAME_CANDIDATE_MIN_SCORE = 85.0

# Top two name matches within this gap are treated as ambiguous.
NAME_AMBIGUOUS_SCORE_GAP = 3.0

RESOLUTION_STATUS_RESOLVED = "resolved"
RESOLUTION_STATUS_AMBIGUOUS = "ambiguous"
RESOLUTION_STATUS_UNRESOLVED = "unresolved"

METHOD_EXACT_PHONE = "exact_phone"
METHOD_EXACT_VEHICLE = "exact_vehicle"
METHOD_EXACT_BANK_ACCOUNT = "exact_bank_account"
METHOD_EXACT_IFSC = "exact_ifsc"
METHOD_FUZZY_NAME = "fuzzy_name"
METHOD_NONE = "none"

# Overlay entity_mapping.source for a human-confirmed canonical assignment.
MAPPING_SOURCE_ADJUDICATION = "adjudication"

IDENTIFIER_ENTITY_TYPES = frozenset(
    {"phone", "vehicle", "bank_account", "ifsc"}
)
NAME_ENTITY_TYPES = frozenset({"person_name", "name", "person"})

# NER types that are extracted but not auto-resolved in the current contract.
NON_RESOLVABLE_NER_ENTITY_TYPES = frozenset({"location", "organisation", "event"})
