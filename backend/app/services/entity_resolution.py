"""
Entity resolution against canonical person and entity-mapping data.

Identifier resolution is exact and runs before any fuzzy person-name matching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict

from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler

from app.services.extraction import (
    EntityCandidate,
    candidate_normalized_value,
    normalize_bank_account,
    normalize_ifsc,
    normalize_phone,
    normalize_vehicle,
)
from app.services.ingestion import load_entity_mapping, load_persons
from app.services.resolution_config import (
    IDENTIFIER_ENTITY_TYPES,
    IDENTIFIER_MATCH_CONFIDENCE,
    MAPPING_SOURCE_ADJUDICATION,
    METHOD_EXACT_BANK_ACCOUNT,
    METHOD_EXACT_IFSC,
    METHOD_EXACT_PHONE,
    METHOD_EXACT_VEHICLE,
    METHOD_FUZZY_NAME,
    METHOD_NONE,
    NAME_AMBIGUOUS_SCORE_GAP,
    NAME_CANDIDATE_MIN_SCORE,
    NAME_ENTITY_TYPES,
    NAME_RESOLVED_MIN_SCORE,
    NON_RESOLVABLE_NER_ENTITY_TYPES,
    RESOLUTION_STATUS_AMBIGUOUS,
    RESOLUTION_STATUS_RESOLVED,
    RESOLUTION_STATUS_UNRESOLVED,
)


class ResolutionResult(TypedDict, total=False):
    candidate_value: str
    entity_type: str
    matched_entity_id: str | None
    confidence: float
    method: str
    status: str
    proposed_entity_ids: list[str]
    candidate_scores: dict[str, float]
    ambiguity_reason: str
    corroborating_evidence: dict[str, Any]
    resolution_note: str


def _add_index_entry(index: dict[str, set[str]], key: str | None, entity_id: str) -> None:
    if not key:
        return
    index.setdefault(key, set()).add(str(entity_id))


def _normalize_identifier(entity_type: str, value: str) -> str:
    if entity_type == "phone":
        return normalize_phone(value)
    if entity_type == "vehicle":
        return normalize_vehicle(value)
    if entity_type == "bank_account":
        return normalize_bank_account(value)
    if entity_type == "ifsc":
        return normalize_ifsc(value)
    return value.strip()


def confirmed_mapping_key(entity_type: str, value: str) -> tuple[str, str] | None:
    """Stable overlay lookup key for a confirmed mention."""
    kind = str(entity_type or "").strip().lower()
    raw = str(value or "").strip()
    if not kind or not raw:
        return None
    if kind in IDENTIFIER_ENTITY_TYPES:
        return (kind, _normalize_identifier(kind, raw))
    if kind in NAME_ENTITY_TYPES:
        return ("person_name", raw.casefold())
    return (kind, raw)


@dataclass
class CanonicalRegistry:
    phones: dict[str, set[str]] = field(default_factory=dict)
    vehicles: dict[str, set[str]] = field(default_factory=dict)
    bank_accounts: dict[str, set[str]] = field(default_factory=dict)
    ifsc_codes: dict[str, set[str]] = field(default_factory=dict)
    person_names: dict[str, str] = field(default_factory=dict)
    confirmed: dict[tuple[str, str], str] = field(default_factory=dict)

    def identifier_index(self, entity_type: str) -> dict[str, set[str]]:
        if entity_type == "phone":
            return self.phones
        if entity_type == "vehicle":
            return self.vehicles
        if entity_type == "bank_account":
            return self.bank_accounts
        if entity_type == "ifsc":
            return self.ifsc_codes
        return {}


def build_canonical_registry() -> CanonicalRegistry:
    """Build lookup indexes from persons.csv and entity_mapping.csv."""
    registry = CanonicalRegistry()

    persons = load_persons()
    for _, row in persons.iterrows():
        person_id = str(row["person_id"])
        name = row.get("name")
        if name:
            registry.person_names[person_id] = str(name).strip()

        _add_index_entry(
            registry.phones,
            normalize_phone(str(row["phone"])) if row.get("phone") else None,
            person_id,
        )
        _add_index_entry(
            registry.vehicles,
            normalize_vehicle(str(row["vehicle_no"])) if row.get("vehicle_no") else None,
            person_id,
        )
        _add_index_entry(
            registry.bank_accounts,
            normalize_bank_account(str(row["bank_account"]))
            if row.get("bank_account")
            else None,
            person_id,
        )

    mapping = load_entity_mapping()
    for _, row in mapping.iterrows():
        entity_id = str(row["entity_id"])
        entity_type = str(row["entity_type"]).strip().lower()
        source_id = row.get("source_id")
        if not source_id:
            continue

        source = str(row.get("source") or "").strip().lower()
        if source == MAPPING_SOURCE_ADJUDICATION:
            confirmed_key = confirmed_mapping_key(entity_type, str(source_id))
            if confirmed_key:
                registry.confirmed[confirmed_key] = entity_id

        if entity_type == "phone":
            _add_index_entry(
                registry.phones,
                normalize_phone(str(source_id)),
                entity_id,
            )
        elif entity_type == "vehicle":
            _add_index_entry(
                registry.vehicles,
                normalize_vehicle(str(source_id)),
                entity_id,
            )
        elif entity_type == "bank_account":
            _add_index_entry(
                registry.bank_accounts,
                normalize_bank_account(str(source_id)),
                entity_id,
            )
        elif entity_type == "ifsc":
            _add_index_entry(
                registry.ifsc_codes,
                normalize_ifsc(str(source_id)),
                entity_id,
            )

    return registry


def _result(
    candidate: EntityCandidate,
    *,
    matched_entity_id: str | None,
    confidence: float,
    method: str,
    status: str,
    proposed_entity_ids: list[str] | None = None,
    candidate_scores: dict[str, float] | None = None,
    ambiguity_reason: str | None = None,
    corroborating_evidence: dict[str, Any] | None = None,
    resolution_note: str | None = None,
) -> ResolutionResult:
    payload: ResolutionResult = ResolutionResult(
        candidate_value=candidate_normalized_value(candidate),
        entity_type=candidate["entity_type"],
        matched_entity_id=matched_entity_id,
        confidence=confidence,
        method=method,
        status=status,
    )
    if proposed_entity_ids is not None:
        payload["proposed_entity_ids"] = proposed_entity_ids
    if candidate_scores is not None:
        payload["candidate_scores"] = candidate_scores
    if ambiguity_reason is not None:
        payload["ambiguity_reason"] = ambiguity_reason
    if corroborating_evidence is not None:
        payload["corroborating_evidence"] = corroborating_evidence
    if resolution_note is not None:
        payload["resolution_note"] = resolution_note
    return payload


def _corroborating_evidence(candidate: EntityCandidate) -> dict[str, Any]:
    return {
        "source": candidate.get("source"),
        "record_id": candidate.get("record_id"),
        "extraction_method": candidate.get("extraction_method"),
        "source_text": candidate.get("source_text"),
        "confidence": candidate.get("confidence"),
    }


def _is_rejected_ambiguity(
    candidate: EntityCandidate,
    *,
    proposed_entity_ids: list[str],
    method: str,
    jurisdiction: str | None,
) -> bool:
    from app.services.adjudication_service import is_candidate_rejected

    return is_candidate_rejected(
        candidate_value=candidate_normalized_value(candidate),
        entity_type=candidate["entity_type"],
        proposed_entity_ids=proposed_entity_ids,
        matching_method=method,
        jurisdiction=jurisdiction,
    )


def _method_for_entity_type(entity_type: str) -> str:
    return {
        "phone": METHOD_EXACT_PHONE,
        "vehicle": METHOD_EXACT_VEHICLE,
        "bank_account": METHOD_EXACT_BANK_ACCOUNT,
        "ifsc": METHOD_EXACT_IFSC,
    }.get(entity_type, METHOD_FUZZY_NAME if entity_type in NAME_ENTITY_TYPES else METHOD_NONE)


def lookup_confirmed_entity_id(
    candidate: EntityCandidate,
    registry: CanonicalRegistry,
) -> str | None:
    key = confirmed_mapping_key(
        candidate["entity_type"],
        candidate_normalized_value(candidate),
    )
    if key is None:
        return None
    return registry.confirmed.get(key)


def _resolve_confirmed_mapping(
    candidate: EntityCandidate,
    registry: CanonicalRegistry,
) -> ResolutionResult | None:
    confirmed_id = lookup_confirmed_entity_id(candidate, registry)
    if not confirmed_id:
        return None
    entity_type = candidate["entity_type"]
    method = _method_for_entity_type(entity_type)
    confidence = (
        IDENTIFIER_MATCH_CONFIDENCE
        if entity_type in IDENTIFIER_ENTITY_TYPES
        else 100.0
    )
    return _result(
        candidate,
        matched_entity_id=confirmed_id,
        confidence=confidence,
        method=method,
        status=RESOLUTION_STATUS_RESOLVED,
        proposed_entity_ids=[confirmed_id],
        corroborating_evidence=_corroborating_evidence(candidate),
        resolution_note="Human reviewer confirmed this canonical entity.",
    )


def _resolve_exact_identifier(
    candidate: EntityCandidate,
    registry: CanonicalRegistry,
    *,
    jurisdiction: str | None = None,
) -> ResolutionResult | None:
    entity_type = candidate["entity_type"]
    if entity_type not in IDENTIFIER_ENTITY_TYPES:
        return None

    method_by_type = {
        "phone": METHOD_EXACT_PHONE,
        "vehicle": METHOD_EXACT_VEHICLE,
        "bank_account": METHOD_EXACT_BANK_ACCOUNT,
        "ifsc": METHOD_EXACT_IFSC,
    }
    method = method_by_type[entity_type]

    key = _normalize_identifier(entity_type, candidate_normalized_value(candidate))
    matches = sorted(registry.identifier_index(entity_type).get(key, set()))
    evidence = _corroborating_evidence(candidate)

    if len(matches) == 1:
        proposed = [matches[0]]
        if _is_rejected_ambiguity(
            candidate,
            proposed_entity_ids=proposed,
            method=method,
            jurisdiction=jurisdiction,
        ):
            return _result(
                candidate,
                matched_entity_id=None,
                confidence=IDENTIFIER_MATCH_CONFIDENCE,
                method=method,
                status=RESOLUTION_STATUS_UNRESOLVED,
                proposed_entity_ids=proposed,
                ambiguity_reason="Human reviewer rejected this candidate merge.",
                corroborating_evidence=evidence,
                resolution_note="Adjudication rejection prevents silent auto-merge.",
            )
        return _result(
            candidate,
            matched_entity_id=matches[0],
            confidence=IDENTIFIER_MATCH_CONFIDENCE,
            method=method,
            status=RESOLUTION_STATUS_RESOLVED,
        )

    if len(matches) > 1:
        if _is_rejected_ambiguity(
            candidate,
            proposed_entity_ids=matches,
            method=method,
            jurisdiction=jurisdiction,
        ):
            return _result(
                candidate,
                matched_entity_id=None,
                confidence=IDENTIFIER_MATCH_CONFIDENCE,
                method=method,
                status=RESOLUTION_STATUS_UNRESOLVED,
                proposed_entity_ids=matches,
                candidate_scores={entity_id: IDENTIFIER_MATCH_CONFIDENCE for entity_id in matches},
                ambiguity_reason="Human reviewer rejected this candidate merge.",
                corroborating_evidence=evidence,
                resolution_note="Adjudication rejection prevents silent auto-merge.",
            )
        return _result(
            candidate,
            matched_entity_id=None,
            confidence=IDENTIFIER_MATCH_CONFIDENCE,
            method=method,
            status=RESOLUTION_STATUS_AMBIGUOUS,
            proposed_entity_ids=matches,
            candidate_scores={entity_id: IDENTIFIER_MATCH_CONFIDENCE for entity_id in matches},
            ambiguity_reason=(
                f"Exact {entity_type} identifier matched {len(matches)} canonical entities."
            ),
            corroborating_evidence=evidence,
        )

    return None


def _name_match_score(query: str, choice: str) -> float:
    """Combine token-set, weighted ratio, and Jaro-Winkler similarity."""
    token_set = float(fuzz.token_set_ratio(query, choice))
    weighted = float(fuzz.WRatio(query, choice))
    jaro = float(JaroWinkler.normalized_similarity(query, choice)) * 100.0
    return max(token_set, weighted, jaro)


def _resolve_fuzzy_name(
    candidate: EntityCandidate,
    registry: CanonicalRegistry,
    *,
    jurisdiction: str | None = None,
) -> ResolutionResult:
    query = candidate_normalized_value(candidate).strip()
    evidence = _corroborating_evidence(candidate)
    if not query:
        return _result(
            candidate,
            matched_entity_id=None,
            confidence=0.0,
            method=METHOD_NONE,
            status=RESOLUTION_STATUS_UNRESOLVED,
        )

    scored: list[tuple[str, float]] = []
    for person_id, name in registry.person_names.items():
        score = _name_match_score(query, name)
        if score >= NAME_CANDIDATE_MIN_SCORE:
            scored.append((person_id, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    candidate_scores = {person_id: score for person_id, score in scored}

    if not scored:
        return _result(
            candidate,
            matched_entity_id=None,
            confidence=0.0,
            method=METHOD_FUZZY_NAME,
            status=RESOLUTION_STATUS_UNRESOLVED,
        )

    top_id, top_score = scored[0]
    second_score = scored[1][1] if len(scored) > 1 else 0.0

    if top_score < NAME_RESOLVED_MIN_SCORE:
        return _result(
            candidate,
            matched_entity_id=None,
            confidence=top_score,
            method=METHOD_FUZZY_NAME,
            status=RESOLUTION_STATUS_UNRESOLVED,
            candidate_scores=candidate_scores,
        )

    if len(scored) > 1 and (top_score - second_score) < NAME_AMBIGUOUS_SCORE_GAP:
        proposed = [person_id for person_id, _ in scored[:3]]
        if _is_rejected_ambiguity(
            candidate,
            proposed_entity_ids=proposed,
            method=METHOD_FUZZY_NAME,
            jurisdiction=jurisdiction,
        ):
            return _result(
                candidate,
                matched_entity_id=None,
                confidence=top_score,
                method=METHOD_FUZZY_NAME,
                status=RESOLUTION_STATUS_UNRESOLVED,
                proposed_entity_ids=proposed,
                candidate_scores=candidate_scores,
                ambiguity_reason="Human reviewer rejected this candidate merge.",
                corroborating_evidence=evidence,
                resolution_note="Adjudication rejection prevents silent auto-merge.",
            )
        return _result(
            candidate,
            matched_entity_id=None,
            confidence=top_score,
            method=METHOD_FUZZY_NAME,
            status=RESOLUTION_STATUS_AMBIGUOUS,
            proposed_entity_ids=proposed,
            candidate_scores=candidate_scores,
            ambiguity_reason=(
                "Top fuzzy name matches are within the ambiguity score gap "
                f"({NAME_AMBIGUOUS_SCORE_GAP})."
            ),
            corroborating_evidence=evidence,
        )

    if _is_rejected_ambiguity(
        candidate,
        proposed_entity_ids=[top_id],
        method=METHOD_FUZZY_NAME,
        jurisdiction=jurisdiction,
    ):
        return _result(
            candidate,
            matched_entity_id=None,
            confidence=top_score,
            method=METHOD_FUZZY_NAME,
            status=RESOLUTION_STATUS_UNRESOLVED,
            proposed_entity_ids=[top_id],
            candidate_scores=candidate_scores,
            ambiguity_reason="Human reviewer rejected this candidate merge.",
            corroborating_evidence=evidence,
            resolution_note="Adjudication rejection prevents silent auto-merge.",
        )

    return _result(
        candidate,
        matched_entity_id=top_id,
        confidence=top_score,
        method=METHOD_FUZZY_NAME,
        status=RESOLUTION_STATUS_RESOLVED,
        candidate_scores=candidate_scores,
    )


def _below_resolution_threshold(candidate: EntityCandidate) -> bool:
    return candidate.get("resolution_eligible") is False


def resolve_candidate(
    candidate: EntityCandidate,
    registry: CanonicalRegistry,
    *,
    jurisdiction: str | None = None,
) -> ResolutionResult:
    """Resolve one extracted candidate against canonical entity indexes."""
    if _below_resolution_threshold(candidate):
        return _result(
            candidate,
            matched_entity_id=None,
            confidence=float(candidate.get("confidence") or 0.0),
            method=METHOD_NONE,
            status=RESOLUTION_STATUS_UNRESOLVED,
        )

    confirmed_result = _resolve_confirmed_mapping(candidate, registry)
    if confirmed_result is not None:
        return confirmed_result

    identifier_result = _resolve_exact_identifier(
        candidate,
        registry,
        jurisdiction=jurisdiction,
    )
    if identifier_result is not None:
        return identifier_result

    entity_type = candidate["entity_type"]
    if entity_type in NON_RESOLVABLE_NER_ENTITY_TYPES:
        return _result(
            candidate,
            matched_entity_id=None,
            confidence=float(candidate.get("confidence") or 0.0),
            method=METHOD_NONE,
            status=RESOLUTION_STATUS_UNRESOLVED,
        )

    if entity_type in NAME_ENTITY_TYPES:
        return _resolve_fuzzy_name(candidate, registry, jurisdiction=jurisdiction)

    return _result(
        candidate,
        matched_entity_id=None,
        confidence=0.0,
        method=METHOD_NONE,
        status=RESOLUTION_STATUS_UNRESOLVED,
    )


def resolve_candidates(
    candidates: list[EntityCandidate],
    registry: CanonicalRegistry | None = None,
    *,
    jurisdiction: str | None = None,
) -> list[ResolutionResult]:
    """Resolve a batch of extracted candidates."""
    active_registry = registry or build_canonical_registry()
    return [
        resolve_candidate(candidate, active_registry, jurisdiction=jurisdiction)
        for candidate in candidates
    ]
